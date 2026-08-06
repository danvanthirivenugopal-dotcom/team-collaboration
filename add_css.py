with open(r'D:\FaceAI_Project(!@#)\frontend\style.css', 'a', encoding='utf-8') as f:
    f.write('\n/* Hide empty iframes */\niframe[height="0"] { display: none !important; margin: 0 !important; padding: 0 !important; border: none !important; }\ndiv[data-testid="stHtml"]:has(iframe[height="0"]) { display: none !important; margin: 0 !important; padding: 0 !important; border: none !important; }\n')
