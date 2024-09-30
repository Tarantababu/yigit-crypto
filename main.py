import streamlit as st
import praw
import requests
import pandas as pd
from datetime import datetime

# Configuration
REDDIT_CLIENT_ID = "Pw30vnSKcyJ5Yp_LeHSLPA"
REDDIT_CLIENT_SECRET = "kmsYDJd8QJ1qSLUOZRS3HNbLBwXomA"
REDDIT_USER_AGENT = "crypto_tracker:v1.0 (by /u/yourusername)"

# Initialize Reddit API
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

def fetch_reddit_posts(subreddit_name, limit=10):
    subreddit = reddit.subreddit(subreddit_name)
    posts = []
    for post in subreddit.new(limit=limit):
        posts.append({
            "title": post.title,
            "url": post.url,
            "score": post.score,
            "created_utc": datetime.fromtimestamp(post.created_utc),
            "source": f"Reddit - r/{subreddit_name}"
        })
    return posts

def fetch_4chan_posts(board, limit=10):
    url = f"https://a.4cdn.org/{board}/catalog.json"
    response = requests.get(url)
    posts = []
    if response.status_code == 200:
        data = response.json()
        for page in data:
            for thread in page['threads']:
                if 'com' in thread:
                    posts.append({
                        "title": thread['com'][:100] + "...",
                        "url": f"https://boards.4chan.org/{board}/thread/{thread['no']}",
                        "score": thread.get('replies', 0),
                        "created_utc": datetime.fromtimestamp(thread['time']),
                        "source": f"4chan - /{board}/"
                    })
                if len(posts) >= limit:
                    break
            if len(posts) >= limit:
                break
    return posts[:limit]

def main():
    st.title("Crypto Project Tracker")

    # Sidebar for user input
    st.sidebar.header("Data Sources")
    use_reddit = st.sidebar.checkbox("Reddit", value=True)
    use_4chan = st.sidebar.checkbox("4chan", value=True)

    # Main content
    if st.button("Fetch New Crypto Projects"):
        all_posts = []

        if use_reddit:
            reddit_subreddits = ["CryptoCurrency", "CryptoMoonShots", "Altcoin", "DeFi", "NFT", "ethtrader", "Bitcoin"]
            for subreddit in reddit_subreddits:
                with st.spinner(f"Fetching posts from r/{subreddit}..."):
                    all_posts.extend(fetch_reddit_posts(subreddit))

        if use_4chan:
            chan_boards = ["biz", "g"]
            for board in chan_boards:
                with st.spinner(f"Fetching posts from 4chan /{board}/..."):
                    all_posts.extend(fetch_4chan_posts(board))

        # Sort posts by creation date
        all_posts.sort(key=lambda x: x['created_utc'], reverse=True)

        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(all_posts)

        # Display posts
        st.subheader("Latest Crypto Projects")
        st.dataframe(df[['title', 'source', 'score', 'created_utc']])

        # Allow user to select a post to view details
        if not df.empty:
            st.subheader("Post Details")
            selected_title = st.selectbox("Select a post to view details:", df['title'].tolist())
            
            if selected_title:
                selected_post = df[df['title'] == selected_title].iloc[0]
                st.markdown(f"**Title:** {selected_post['title']}")
                st.markdown(f"**Source:** {selected_post['source']}")
                st.markdown(f"**Score:** {selected_post['score']}")
                st.markdown(f"**Created:** {selected_post['created_utc']}")
                st.markdown(f"**URL:** [{selected_post['url']}]({selected_post['url']})")
        else:
            st.warning("No posts were fetched. Try selecting different data sources or try again later.")

if __name__ == "__main__":
    main()
