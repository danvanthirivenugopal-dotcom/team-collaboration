import re
import os

filepath = r"D:\FaceAI_Project(!@#)\frontend\modules\scanner.py"
with open(filepath, 'r', encoding='utf-8') as f:
    c = f.read()

# Fix Python messages
c = c.replace('st.session_state.status_message = ("info", "ℹ️ Okay, attendance unchanged.")',
              'st.session_state.status_message = ("info", "Attendance remains active. Checkout was not marked.")')
c = c.replace('st.session_state.status_message = ("success", f"✅ Check-Out successful! Have a great day.")',
              'st.session_state.status_message = ("success", f"{user_name}, checkout time successfully marked.")')

# Replace the exact JS JS toast blocks.
# The original code looks like this:
old_js_block = """
                                    const cd = cooldowns.get("act_" + uid) || 0;
                                    if (now - cd > 30000) {
                                        if (status === "checked_in") {
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`✅ ${name}, attendance successfully marked.`, "success");
                                        } else if (status === "already_completed") {
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`ℹ️ ${name}, attendance already completed today.`, "info");
                                        } else if (status === "not_approved") {
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`⏳ ${name}, your account is pending admin approval.`, "warning");
                                        } else if (status === "location_error") {
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`🚫 ${name}, you are not in the approved location.`, "error");
                                        } else if (status === "method_mismatch") {
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`⚠️ ${name}'s attendance is mapped to fingerprint.`, "error");
                                        }
                                    }
                                }
                            }
"""

new_js_block = """
                                    const cd = cooldowns.get("act_" + uid) || 0;
                                    if (now - cd > 30000) {
                                        if (status === "checked_in") {
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${name}, attendance successfully marked.`, "success");
                                        } else if (status === "already_completed") {
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${name}, today's attendance is already completed.`, "info");
                                        } else if (status === "not_approved") {
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${name}, your account is awaiting approval. Attendance cannot be marked.`, "warning");
                                        } else if (status === "location_error") {
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${name}, you are not in the approved location.`, "error");
                                        } else if (status === "method_mismatch") {
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${name}'s attendance is mapped to fingerprint.`, "error");
                                        }
                                    }
                                }
                            } else {
                                const cd = cooldowns.get("act_unknown") || 0;
                                if (now - cd > 30000) {
                                    if (status === "unknown") {
                                        cooldowns.set("act_unknown", now);
                                        showToast("Unknown user detected. No attendance was marked.", "error");
                                    } else if (status === "multiple_faces") {
                                        cooldowns.set("act_unknown", now);
                                        showToast("Multiple faces detected. Only one person can mark attendance at a time.", "error");
                                    }
                                }
                            }
"""

# Because of emojis in original code, regex is safer:
old_pattern = re.compile(r'const cd = cooldowns\.get\("act_" \+ uid\) \|\| 0;\s*if \(now - cd > 30000\) \{.*?showToast\(`.*?\$\[name\}.*?`, "error"\);\s*\}\s*\}\s*\}\s*\}', re.DOTALL)
c = c.replace(old_js_block.strip(), new_js_block.strip())

# The emojis might not match exactly due to character encoding, let's use a simpler replace
# by just finding the blocks
c = re.sub(
    r'const cd = cooldowns\.get\("act_" \+ uid\) \|\| 0;\s*if \(now - cd > 30000\) \{.*?\}\s*\}\s*\}',
    new_js_block.strip(), 
    c, 
    flags=re.DOTALL
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(c)
print("Updated js blocks successfully.")
