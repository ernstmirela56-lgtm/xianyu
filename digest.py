import os, ssl, smtplib, html, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from email.message import EmailMessage
from bs4 import BeautifulSoup

def main():
    required = ["SMTP_USER", "SMTP_PASSWORD", "MAIL_TO"]
    if any(not os.getenv(k) for k in required):
        raise RuntimeError("Configure SMTP_USER, SMTP_PASSWORD and MAIL_TO in Actions secrets")
    req = urllib.request.Request("https://github.com/trending?since=daily", headers={"User-Agent": "daily-github-digest"})
    with urllib.request.urlopen(req, timeout=45) as response:
        soup = BeautifulSoup(response.read(), "html.parser")
    rows = []
    for article in soup.select("article.Box-row"):
        link = article.select_one("h2 a")
        if not link:
            continue
        name = "".join(link.get_text().split())
        description = article.select_one("p")
        language = article.select_one('[itemprop="programmingLanguage"]')
        daily = article.select_one("span.d-sm-inline-block.float-sm-right")
        rows.append((name, "https://github.com" + link["href"], description.get_text(" ", strip=True) if description else "暂无简介", language.get_text(strip=True) if language else "未标注", daily.get_text(" ", strip=True) if daily else "未提供"))
        if len(rows) == 10:
            break
    if not rows:
        raise RuntimeError("Trending returned no projects; refusing to send empty ranking")
    date = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    body = [f"<h2>GitHub 每日热门项目 · {date}</h2>", "<p>来源：GitHub Trending 每日榜。这是热门趋势，非实际搜索量；许可证请以仓库为准。</p>"]
    if len(rows) < 10:
        body.append(f"<p>今日页面仅获取到 {len(rows)} 个项目。</p>")
    for i, (name, url, desc, lang, stars) in enumerate(rows, 1):
        body.append(f'<h3>{i}. <a href="{html.escape(url)}">{html.escape(name)}</a></h3><p>{html.escape(desc)}</p><p>语言：{html.escape(lang)} · {html.escape(stars)}</p>')
    body.append('<p><a href="https://github.com/trending?since=daily">查看原始榜单</a></p>')
    msg = EmailMessage()
    msg["Subject"] = f"GitHub 每日热门项目 Top 10 | {date}"
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = os.environ["MAIL_TO"]
    msg.set_content("今日 GitHub 热门项目：\n" + "\n".join(f"{i}. {r[0]} {r[1]} — {r[2]}" for i, r in enumerate(rows, 1)))
    msg.add_alternative("".join(body), subtype="html")
    with smtplib.SMTP_SSL(os.getenv("SMTP_HOST", "smtp.qq.com"), int(os.getenv("SMTP_PORT", "465")), context=ssl.create_default_context(), timeout=45) as smtp:
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)
    print(f"Sent {len(rows)} projects successfully")

if __name__ == "__main__":
    main()
