from requests import Session

from src.tool.auth import create_authenticated_session, LoginException


def get_html(url: str, session: Session = None) -> str:
    """获取网页内容"""
    try:
        # 复用会话或创建新会话
        if not session or not isinstance(session, Session):
            session = create_authenticated_session()

        print(f"正在访问 {url}")
        response = session.get(url, timeout=15)
        response.encoding = 'gbk'

        # 检查是否被登出
        if '请先登录' in response.text:
            raise LoginException("会话已过期，需要重新登录")

        return response.text

    except Exception as e:
        print(f"请求失败: {str(e)}")
        return None