import requests
import json
import time

# --- 配置文件加载 ---
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    COOKIE = config.get('cookie')
    GEMINI_API_KEY = config.get('openai_api_key')
    MODEL_NAME = config.get('openai_model_name', 'gemini-1.5-flash')
    SYSTEM_PROMPT = config.get('system_prompt', '你是一个友好且乐于助人的助手。')

    if not COOKIE or "粘贴" in COOKIE:
        print("错误：请先在 config.json 文件中设置你的爱发电Cookie。")
        exit()
    if not GEMINI_API_KEY or "粘贴" in GEMINI_API_KEY:
        print("错误：请先在 config.json 文件中设置你的 API Key。")
        exit()

except FileNotFoundError:
    print("错误：找不到 config.json 文件。")
    exit()
except Exception as e:
    print(f"初始化失败: {e}")
    exit()

# --- 爱发电接口地址 ---
API_BASE_URL = "https://afdian.com/api"
GET_DIALOGS_URL = f"{API_BASE_URL}/message/dialogs"
SEND_MSG_URL = f"{API_BASE_URL}/message/send"
MARK_AS_READ_URL = f"{API_BASE_URL}/message/messages"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'Content-Type': 'application/json',
    'Cookie': COOKIE,
    'accept': 'application/json, text/plain, */*',
    'origin': 'https://afdian.com',
    'referer': 'https://afdian.com/message'
}

def get_unread_dialogs():
    """获取未读消息列表"""
    params = {'unread': '1', 'page': '1'}
    try:
        response = requests.get(GET_DIALOGS_URL, headers=HEADERS, params=params)
        data = response.json()
        if data.get('ec') == 200:
            return data.get('data', {}).get('list', [])
        return []
    except:
        return []

def send_reply(user_id, content):
    """发送回复并打印完整响应"""
    payload = {'user_id': user_id, 'content': content, 'type': '1'}
    try:
        response = requests.post(SEND_MSG_URL, headers=HEADERS, json=payload)
        data = response.json()
        # 看看 data 里面是否有新生成的 message_id
        print(f"爱发电原始响应: {data}") 
        
        if data.get('ec') == 200:
            # 如果 data 里面有 message_id，说明消息确实存入数据库了
            return True
        return False
    except Exception as e:
        print(f"发送异常: {e}")
        return False
def mark_as_read(user_id):
    """标记对话为已读"""
    params = {'user_id': user_id, 'type': 'old', 'message_id': ''}
    try:
        requests.get(MARK_AS_READ_URL, headers=HEADERS, params=params)
        return True
    except:
        return False

def get_gemini_reply(prompt):
    """使用 v1beta 路径对齐最新的 gemini-2.5-flash"""
    # 强制使用 v1beta，因为 2.5 模型目前主要在 beta 路径
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Instructions: {SYSTEM_PROMPT}\n\nUser: {prompt}"}]
        }]
    }
    
    try:
        print(f"正在生成 AI 回复 (模型: {MODEL_NAME})...")
        response = requests.post(url, json=payload, timeout=30)
        
        # 如果报错，打印详细信息以便排查
        if response.status_code != 200:
            print(f"API 错误详情: {response.text}")
            return "抱歉，我的大脑暂时断网了。"

        data = response.json()
        # 增加解析安全性检查
        if 'candidates' in data and data['candidates']:
            reply = data['candidates'][0]['content']['parts'][0]['text'].strip()
            final_reply = f"{reply}\n\n(此回复由AI生成)"
            print(f"成功回复: {reply[:20]}...")
            return final_reply
        else:
            print(f"Google 返回了空结果: {data}")
            return "抱歉，我还没想好怎么回。"
            
    except Exception as e:
        print(f"脚本执行出错: {e}")
        return "系统繁忙，请稍后再试。"
    


def main_loop():
    print("机器人已启动，使用原生 REST API 模式...")
    while True:
        try:
            unread_dialogs = get_unread_dialogs()
            if unread_dialogs:
                for dialog in unread_dialogs:
                    user_id = dialog.get('user', {}).get('user_id')
                    message_content = dialog.get('desc')
                    if user_id:
                        print(f"收到消息: {message_content}")
                        reply_content = get_gemini_reply(message_content)
                        if send_reply(user_id, reply_content):
                            mark_as_read(user_id)
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 暂无新消息...")
            
            time.sleep(15)
        except KeyboardInterrupt:
            print("\n已停止运行。")
            break
        except Exception as e:
            print(f"循环错误: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
