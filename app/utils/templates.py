import json

def get_empty_forwards_text() -> str:
    return (
        "*No Forwards Yet* 🤷‍♂️\n\n"
        "It looks like you haven't set up any rules.\n"
        "Click *[➕ New Forward]* in the main menu to get started!"
    )

def get_forwards_list_header() -> str:
    return (
        "📂 *Your Forwards*\n"
        "──────────────\n"
        "Tap an item to manage or edit:"
    )

def get_forward_detail_text(details: dict, dests: list) -> str:
    status_icon = "🔴" if details['paused'] else "🟢"
    status_text = "Paused" if details['paused'] else "Active"
    source_chat = details['source_title'] or "Unknown"
    
    dest_text = ""
    if not dests:
        dest_text = " None"
    else:
        for i, dest in enumerate(dests, 1):
            dest_text += f"\n   └ {dest['title']}"
            
    try:
        filters_list = json.loads(details['filters'])
    except Exception:
        filters_list = []

    content_filters = [f.title() for f in filters_list if f != 'sender']
    filters_str = ", ".join(content_filters) if content_filters else "None"
    
    sender_mode = "Show Sender" if "sender" in filters_list else "Hide Sender (Copy)"
    
    schedule_line = ""
    if details['schedule_time']:
        schedule_line = f"• Schedule: 🕒 {details['schedule_time']}\n"
        
    return (
        f"📱 *{details['name']}*\n"
        f"──────────────\n"
        f"{status_icon} *Status:* {status_text}\n"
        f"📤 *Source:* {source_chat}\n"
        f"📥 *Destination(s):*{dest_text}\n\n"
        f"⚙️ *Configuration*\n"
        f"• Filters: {filters_str}\n"
        f"• Mode: {sender_mode}\n"
        f"{schedule_line}"
    )

def get_forward_rules_text(details: dict) -> str:
    return (
        f"*Rules for {details['name']}*\n\n"
        "Toggle content types to forward.\n"
        "*Show Sender*: Forward message (with tag).\n"
        "*Hide Sender*: Copy message (no tag)."
    )

def get_clear_dest_text() -> str:
    return "*Clear Destination*\n\nSelect which destination(s) to clear:"

def get_edit_dest_text(pos: int) -> str:
    return f"*Select Chat for Destination {pos}*"

def get_edit_source_text() -> str:
    return "*Select New Source Chat*"

def get_schedule_prompt_text(fw_id: int) -> str:
    return (
        f"*Set Schedule for Forward {fw_id}*\n\n"
        "Send the daily time in `HH:MM` format (24h), e.g., `09:00` or `18:30`.\n"
        "Send `off` to disable scheduling."
    )
