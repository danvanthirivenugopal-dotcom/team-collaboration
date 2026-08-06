import sys
with open(r'D:\FaceAI_Project(!@#)\frontend\modules\scanner.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_block = '''                        results.forEach(item => {{
                            if (!item.bbox || item.bbox.length !== 4) return;
                            
                            const status = item.status;
                            const name = item.name || "Unknown";
                            const uid = item.user_id;
                            
                            let boxColor = "#ef4444"; // red
                            let statusText = "UNKNOWN";
                            
                            if (status === "recognized" || status === "checked_in") {{
                                boxColor = "#00ffff"; // cyan
                                statusText = "MARKED";
                            }} else if (["already_marked", "already_completed", "ask_leave"].includes(status)) {{
                                boxColor = "#00ffff";
                                statusText = "ALREADY MARKED";
                            }} else if (status === "disabled") {{
                                boxColor = "#f59e0b";
                                statusText = "INACTIVE";
                            }} else if (status === "not_approved") {{
                                boxColor = "#f59e0b";
                                statusText = "PENDING";
                            }} else if (status === "location_error") {{
                                boxColor = "#f59e0b";
                                statusText = "LOCATION ERROR";
                            }} else if (status === "method_mismatch") {{
                                boxColor = "#f59e0b";
                                statusText = "FINGERPRINT ONLY";
                            }}
                            
                            drawBoundingBox(item.bbox, `${{name.toUpperCase()}} (${{statusText}})`, uid ? `ID: STU${{100+uid}}` : "Unregistered", boxColor);
                            
                            // Process status logic and notifications
                            if (uid) {{
                                if (status === "ask_checkout") {{
                                    const cd = cooldowns.get("ask_" + uid) || 0;
                                    if (now - cd > 15000) {{
                                        cooldowns.set("ask_" + uid, now);
                                        // Redirect parent to show checkout dialog
                                        try {{
                                            const url = new URL(window.parent.location.href);
                                            url.searchParams.set('fc_status', 'ask_checkout');
                                            url.searchParams.set('fc_user_id', uid);
                                            url.searchParams.set('fc_name', name);
                                            url.searchParams.set('fc_role', item.role || 'user');
                                            window.parent.location.href = url.href;
                                        }} catch(e) {{
                                            showToast("⚠️ Could not trigger checkout. Parent frame blocked.", "error");
                                        }}
                                    }}
                                }} else {{
                                    const cd = cooldowns.get("act_" + uid) || 0;
                                    if (now - cd > 30000) {{
                                        if (status === "checked_in") {{
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${{name}}, attendance successfully marked.`, "success");
                                        }} else if (status === "already_completed") {{
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${{name}}, today's attendance is already completed.`, "info");
                                        }} else if (status === "disabled") {{
                                            cooldowns.set("act_" + uid, now);
                                            showToast("This account is inactive. Contact your organization administrator.", "error");
                                        }} else if (status === "not_approved") {{
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${{name}}, your account is awaiting approval. Attendance cannot be marked.`, "warning");
                                        }} else if (status === "location_error") {{
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${{name}}, you are not in the approved location.`, "error");
                                        }} else if (status === "method_mismatch") {{
                                            cooldowns.set("act_" + uid, now);
                                            showToast(`${{name}}'s attendance is mapped to fingerprint.`, "error");
                                        }}
                                    }}
                                }}
                            }} else {{
                                const cd = cooldowns.get("act_unknown") || 0;
                                if (now - cd > 30000) {{
                                    if (status === "unknown") {{
                                        cooldowns.set("act_unknown", now);
                                        showToast("Unknown user detected. No attendance was marked.", "error");
                                    }} else if (status === "multiple_faces") {{
                                        cooldowns.set("act_unknown", now);
                                        showToast("Multiple faces detected. Only one person can mark attendance at a time.", "error");
                                    }}
                                }}
                            }}
                        }});\n'''

new_lines = lines[:719] + [new_block] + lines[874:]
with open(r'D:\FaceAI_Project(!@#)\frontend\modules\scanner.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
