import streamlit as st
import praw
import requests
import pandas as pd
from datetime import datetime

# Configuration
st.set_page_config(page_title="Crypto Project Tracker", layout="wide")

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

    # Initialize session state
    if 'all_posts' not in st.session_state:
        st.session_state.all_posts = []

    # Main content
    if st.button("Fetch New Crypto Projects"):
        st.session_state.all_posts = []

        if use_reddit:
            reddit_subreddits = [
                "CryptoCurrency", "CryptoMarkets", "Altcoin", "Bitcoin", "Ethereum", "NFT",
                "CryptoMoonShots", "DeFi", "DefiDegens", "ethtrader", "Chainlink", "VeChain",
                "CryptoTechnology", "CryptoGems", "CryptoInvesting", "CryptoTraders",
                "cryptomoonshots", "cryptocommunity", "darknetmarkets", "Crypto_Startup",
                "BitcoinBeginners", "Blockchain", "Crypto_Fraud", "ledger"
            ]
            for subreddit in reddit_subreddits:
                with st.spinner(f"Fetching posts from r/{subreddit}..."):
                    st.session_state.all_posts.extend(fetch_reddit_posts(subreddit))

        if use_4chan:
            chan_boards = ["biz", "g"]
            for board in chan_boards:
                with st.spinner(f"Fetching posts from 4chan /{board}/..."):
                    st.session_state.all_posts.extend(fetch_4chan_posts(board))

        # Sort posts by creation date
        st.session_state.all_posts.sort(key=lambda x: x['created_utc'], reverse=True)

    # Display posts
    if st.session_state.all_posts:
        st.subheader("Latest Crypto Projects")
        df = pd.DataFrame(st.session_state.all_posts)
        st.dataframe(df[['title', 'source', 'score', 'created_utc']])

        # Debug information
        st.write(f"Number of posts: {len(st.session_state.all_posts)}")

        # Allow user to select a post to view details
        st.subheader("Post Details")
        selected_index = st.selectbox(
            "Select a post to view details:",
            options=range(len(st.session_state.all_posts)),
            format_func=lambda i: st.session_state.all_posts[i]['title'][:50] + "..."
        )

        # Debug information
        st.write(f"Selected index: {selected_index}")

        if selected_index is not None:
            selected_post = st.session_state.all_posts[selected_index]
            st.markdown(f"**Title:** {selected_post['title']}")
            st.markdown(f"**Source:** {selected_post['source']}")
            st.markdown(f"**Score:** {selected_post['score']}")
            st.markdown(f"**Created:** {selected_post['created_utc']}")
            st.markdown(f"**URL:** [{selected_post['url']}]({selected_post['url']})")
    else:
        st.warning("No posts fetched yet. Click 'Fetch New Crypto Projects' to load posts.")

if __name__ == "__main__":
    main()
