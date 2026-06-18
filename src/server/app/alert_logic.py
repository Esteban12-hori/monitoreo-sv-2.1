
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
import json
import time
from .models import Server, AlertRecipient, User, AlertRule, NotificationRule, UserGroup
from .email_utils import send_alert_email
from .notification_utils import send_webhook_notification, send_sms_notification, send_whatsapp_notification
from .alert_dispatcher import send_multichannel_alert

def get_alert_recipients(sess: Session, server: Server, alert_type: str) -> tuple[list, list[str]]:
    applied_rules_info = []
    recipients = []

    # 1. External AlertRecipients (Always receive)
    global_recipients = sess.execute(select(AlertRecipient)).scalars().all()
    for r in global_recipients:
        recipients.append({
            "email": r.email, 
            "name": r.name,
            "phone_number": r.phone_number,
            "webhook_url": r.webhook_url
        })
    if global_recipients:
        applied_rules_info.append("Global AlertRecipients")

    # 2. Process Users with new Notification Rules logic
    # Pre-fetch relevant rules
    relevant_rules = sess.execute(select(NotificationRule).where(
        or_(
            NotificationRule.server_id == server.server_id,
            NotificationRule.server_id == None
        )
    )).scalars().all()
    
    # Organize rules
    user_rules_map = {} # user_id -> {'server': Action, 'global': Action}
    group_rules_map = {} # group_id -> {'server': Action, 'global': Action}
    
    for rule in relevant_rules:
        if rule.user_id:
            if rule.user_id not in user_rules_map:
                user_rules_map[rule.user_id] = {}
            key = 'server' if rule.server_id else 'global'
            user_rules_map[rule.user_id][key] = rule.action
            
        if rule.group_id:
            if rule.group_id not in group_rules_map:
                group_rules_map[rule.group_id] = {}
            key = 'server' if rule.server_id else 'global'
            group_rules_map[rule.group_id][key] = rule.action

    # Iterate all users (optimize: only fetch non-blocked)
    all_users = sess.execute(select(User).where(User.is_blocked == False)).scalars().all()
    users_added_count = 0

    for user in all_users:
        should_send = False
        
        # 1. User Rules Priority
        u_rules = user_rules_map.get(user.id, {})
        
        if 'server' in u_rules:
            # Explicit rule for this server
            should_send = (u_rules['server'] == 'ALLOW')
        elif 'global' in u_rules:
            # Explicit global rule for this user
            should_send = (u_rules['global'] == 'ALLOW')
        else:
            # 2. Group Rules Priority
            # Check all groups
            group_actions_server = []
            group_actions_global = []
            
            # Use user.groups (assumed loaded)
            for group in user.groups:
                g_rules = group_rules_map.get(group.id, {})
                if 'server' in g_rules:
                    group_actions_server.append(g_rules['server'])
                if 'global' in g_rules:
                    group_actions_global.append(g_rules['global'])
            
            if group_actions_server:
                # If any group says BLOCK, we BLOCK (conservative)
                should_send = ('BLOCK' not in group_actions_server)
                # If all are ALLOW, then True. If mixed, False.
                # Wait, if I have Group A (Allow) and Group B (nothing), I should get it?
                # The logic `BLOCK not in actions` implies that if ANY is ALLOW, we default to True unless BLOCKED?
                # No, if `group_actions_server` has content, it means we have explicit rules.
                # If I have Group A (ALLOW) and Group B (ALLOW), result is True.
                # If I have Group A (ALLOW) and Group B (BLOCK), result is False.
                # If I have Group A (ALLOW), result is True.
                # If I have Group A (BLOCK), result is False.
                # So `BLOCK not in actions` works IF we assume presence in list implies at least one rule exists.
                pass 
            elif group_actions_global:
                should_send = ('BLOCK' not in group_actions_global)
            else:
                # 3. Fallback to Legacy Logic
                if user.receive_alerts:
                    if user.is_admin:
                        should_send = True
                    else:
                        # Check legacy server assignment
                        if any(s.server_id == server.server_id for s in user.servers):
                            should_send = True

        if should_send:
            recipients.append({"email": user.email, "name": user.name})
            users_added_count += 1

    if users_added_count > 0:
        applied_rules_info.append(f"Subscribed Users ({users_added_count})")
    
    # 3. Alert Rules (Legacy/Recipient matching)
    rules_query = select(AlertRule).where(AlertRule.alert_type == alert_type)
    
    conditions = [AlertRule.server_scope == 'global']
    conditions.append((AlertRule.server_scope == 'server') & (AlertRule.target_id == server.server_id))
    if server.group_name:
        conditions.append((AlertRule.server_scope == 'group') & (AlertRule.target_id == server.group_name))
    
    rules = sess.execute(rules_query.where(or_(*conditions))).scalars().all()

    for r in rules:
        applied_rules_info.append(f"Rule(id={r.id}, scope={r.server_scope}, target={r.target_id})")
        try:
            emails = json.loads(r.emails)
            for email in emails:
                recipients.append({"email": email, "name": "Rule Recipient"})
        except:
            pass

    unique = {r["email"]: r for r in recipients}.values()
    return list(unique), applied_rules_info

def explain_alert_decision(sess: Session, user_id: int, server_id: str) -> dict:
    """
    Analyzes why a user would or would not receive an alert for a specific server.
    Returns a dict with 'decision' (bool) and 'reason' (str) and 'trace' (list of steps).
    """
    user = sess.get(User, user_id)
    if not user:
        return {"decision": False, "reason": "User not found", "trace": []}
    
    server = sess.execute(select(Server).where(Server.server_id == server_id)).scalar_one_or_none()
    # If server doesn't exist in DB yet (e.g. hypothetical), we treat as generic
    
    trace = []
    
    # Fetch rules
    rules_query = select(NotificationRule).where(
        or_(
            NotificationRule.user_id == user_id,
            NotificationRule.group_id.in_([g.id for g in user.groups])
        )
    )
    rules = sess.execute(rules_query).scalars().all()
    
    # 1. User Rules
    user_rules = [r for r in rules if r.user_id == user_id]
    
    # Check for User-Server Specific Rule
    server_rule = next((r for r in user_rules if r.server_id == server_id), None)
    if server_rule:
        decision = (server_rule.action == 'ALLOW')
        trace.append(f"Found explicit user rule for server '{server_id}': {server_rule.action}")
        return {"decision": decision, "reason": f"Explicit User Rule: {server_rule.action}", "trace": trace}
        
    # Check for User Global Rule
    global_rule = next((r for r in user_rules if r.server_id is None), None)
    if global_rule:
        decision = (global_rule.action == 'ALLOW')
        trace.append(f"Found explicit user global rule: {global_rule.action}")
        return {"decision": decision, "reason": f"User Global Rule: {global_rule.action}", "trace": trace}
        
    trace.append("No explicit user rules found.")
    
    # 2. Group Rules
    # We need to check ALL groups. 
    # Logic: If ANY group BLOCKS -> BLOCK.
    # If NO group blocks, but SOME group ALLOWS -> ALLOW.
    # If NO group rules at all -> Legacy.
    
    group_rules = [r for r in rules if r.group_id is not None]
    
    # Filter for relevant rules (Targeting this server or Global)
    relevant_group_rules = []
    for r in group_rules:
        if r.server_id == server_id:
            relevant_group_rules.append((r, 'server'))
        elif r.server_id is None:
            relevant_group_rules.append((r, 'global'))
            
    if relevant_group_rules:
        # Check for BLOCKs first
        blockers = [r for r, scope in relevant_group_rules if r.action == 'BLOCK']
        if blockers:
            blocker = blockers[0]
            group_name = next((g.name for g in user.groups if g.id == blocker.group_id), "Unknown Group")
            trace.append(f"Blocked by group '{group_name}' rule ({'Global' if blocker.server_id is None else 'Server'})")
            return {"decision": False, "reason": f"Blocked by Group '{group_name}'", "trace": trace}
            
        # If no blocks, check for ALLOWs
        # (This implies if ANY group allows and none block, we allow)
        allowers = [r for r, scope in relevant_group_rules if r.action == 'ALLOW']
        if allowers:
            allower = allowers[0]
            group_name = next((g.name for g in user.groups if g.id == allower.group_id), "Unknown Group")
            trace.append(f"Allowed by group '{group_name}' rule")
            return {"decision": True, "reason": f"Allowed by Group '{group_name}'", "trace": trace}
            
    trace.append("No relevant group rules found.")

    # 3. Legacy Fallback
    if not user.receive_alerts:
        trace.append("User 'receive_alerts' is False")
        return {"decision": False, "reason": "Global receive_alerts is OFF", "trace": trace}
        
    if user.is_admin:
        trace.append("User is Admin (Legacy: Always receive)")
        return {"decision": True, "reason": "Admin User (Legacy)", "trace": trace}
        
    # Check legacy server assignment
    # We need to check if this server is in user.servers
    # Note: If server object wasn't found, we can't check relationship easily unless we use ID
    if server:
        is_assigned = server in user.servers
        trace.append(f"Legacy server assignment check: {'Assigned' if is_assigned else 'Not Assigned'}")
        return {"decision": is_assigned, "reason": f"Legacy Assignment: {is_assigned}", "trace": trace}
    else:
        # Fallback if server doesn't exist in DB (e.g. testing with random ID)
        trace.append("Server not found in DB, assuming Not Assigned")
        return {"decision": False, "reason": "Server not found", "trace": trace}


# --- Advanced Alert Logic ---

def evaluate_value(value, op, limit):
    if value is None or limit is None: return False
    try:
        if op == 'gt': return value > limit
        if op == 'lt': return value < limit
        if op == 'eq': return value == limit
        if op == 'gte': return value >= limit
        if op == 'lte': return value <= limit
    except:
        return False
    return False

def get_metric_value(payload, field):
    # payload is Pydantic model
    parts = field.split('.')
    val = payload
    try:
        for p in parts:
            if hasattr(val, p):
                val = getattr(val, p)
            elif isinstance(val, dict):
                val = val.get(p)
            else:
                return None
        return val
    except:
        return None

def check_advanced_rules(sess: Session, server: Server, metrics_payload, alert_state: dict):
    """
    Evaluates rules that have explicit conditions (condition_field set).
    """
    # Fetch relevant rules
    conditions = [AlertRule.server_scope == 'global']
    conditions.append((AlertRule.server_scope == 'server') & (AlertRule.target_id == server.server_id))
    if server.group_name:
        conditions.append((AlertRule.server_scope == 'group') & (AlertRule.target_id == server.group_name))
    
    # Only fetch rules with conditions
    rules = sess.execute(select(AlertRule).where(
        or_(*conditions)
    ).where(AlertRule.condition_field.is_not(None))).scalars().all()
    
    current_time = time.time()
    
    for r in rules:
        val = get_metric_value(metrics_payload, r.condition_field)
        limit = r.condition_value
        op = r.condition_op
        
        # State key: (server_id, rule_id)
        state_key = f"{server.server_id}_rule_{r.id}"
        state = alert_state.get(state_key, {"start": 0, "last_sent": 0})
        
        is_triggered = evaluate_value(val, op, limit)
        
        if is_triggered:
            if state["start"] == 0:
                state["start"] = current_time
            
            duration = current_time - state["start"]
            required_duration = r.duration_seconds or 0
            
            if duration >= required_duration:
                # Cooldown check (e.g. 1 hour)
                if current_time - state["last_sent"] > 3600:
                    print(f"[ADVANCED ALERT] Triggered {r.alert_type} on {server.server_id}: {r.condition_field}={val} {op} {limit}")
                    
                    # Calculate recipients
                    recipients, _ = get_alert_recipients(sess, server, r.alert_type)
                    # Add specific rule emails
                    try:
                        rule_emails = json.loads(r.emails)
                        for email in rule_emails:
                            recipients.append({"email": email, "name": "Rule Specific"})
                    except:
                        pass
                    
                    # Deduplicate
                    unique_recipients = {x["email"]: x for x in recipients}.values()
                    
                    send_multichannel_alert(
                        server_id=server.server_id,
                        alert_type=f"{r.alert_type} ({r.severity})",
                        current_value=val,
                        threshold=limit,
                        recipients=list(unique_recipients),
                        full_metrics=metrics_payload.model_dump()
                    )
                    state["last_sent"] = current_time
        else:
            state["start"] = 0 # Reset
            
        alert_state[state_key] = state
