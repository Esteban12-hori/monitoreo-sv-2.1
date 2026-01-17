
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
import json
import time
from .models import Server, AlertRecipient, User, AlertRule
from .email_utils import send_alert_email

def get_alert_recipients(sess: Session, server: Server, alert_type: str) -> tuple[list, list[str]]:
    applied_rules_info = []

    # 1. Global AlertRecipients
    global_recipients = sess.execute(select(AlertRecipient)).scalars().all()
    recipients = [{"email": r.email, "name": r.name} for r in global_recipients]
    if global_recipients:
        applied_rules_info.append("Global AlertRecipients")

    # 2. Users with receive_alerts=True (Global subscription)
    alert_users = sess.execute(select(User).where(User.receive_alerts == True)).scalars().all()
    users_added = 0
    for u in alert_users:
        # Include if admin OR has access to this server
        if u.is_admin or any(s.server_id == server.server_id for s in u.servers):
            recipients.append({"email": u.email, "name": u.name})
            users_added += 1
    if users_added > 0:
        applied_rules_info.append(f"Subscribed Users ({users_added})")
    
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
                    
                    send_alert_email(
                        server_id=server.server_id,
                        alert_type=f"{r.alert_type} ({r.severity})",
                        current_value=val,
                        threshold=limit,
                        extra_recipients=list(unique_recipients),
                        full_metrics=metrics_payload.model_dump()
                    )
                    state["last_sent"] = current_time
        else:
            state["start"] = 0 # Reset
            
        alert_state[state_key] = state
