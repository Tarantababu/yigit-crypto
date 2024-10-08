import streamlit as st
import praw
import prawcore
import requests
import pandas as pd
from datetime import datetime
import time
from textblob import TextBlob
import re

# Configuration
st.set_page_config(page_title="Crypto Project Tracker", layout="wide")

REDDIT_CLIENT_ID = "Pw30vnSKcyJ5Yp_LeHSLPA"
REDDIT_CLIENT_SECRET = "kmsYDJd8QJ1qSLUOZRS3HNbLBwXomA"
REDDIT_USER_AGENT = "crypto_tracker:v1.0 (by /u/yourusername)"

# Initialize Reddit API
try:
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )
    st.sidebar.success("Successfully connected to Reddit API")
except Exception as e:
    st.sidebar.error(f"Failed to connect to Reddit API: {str(e)}")
    reddit = None

def extract_tokens(text):
    tokens = re.findall(r'\b[A-Z]{2,10}\b', text)
    return [token for token in tokens if token not in ['NFT', 'DeFi', 'CEO', 'ICO', 'AMA']]

def analyze_sentiment(text):
    analysis = TextBlob(text)
    sentiment_score = analysis.sentiment.polarity
    if sentiment_score > 0.05:
        return "Positive", sentiment_score
    elif sentiment_score < -0.05:
        return "Negative", sentiment_score
    else:
        return "Neutral", sentiment_score

def fetch_reddit_posts(subreddit_name, limit=10):
    if reddit is None:
        st.warning(f"Skipping r/{subreddit_name} due to Reddit API connection issues")
        return []

    try:
        subreddit = reddit.subreddit(subreddit_name)
        posts = []
        for post in subreddit.new(limit=limit):
            sentiment, score = analyze_sentiment(post.title + " " + post.selftext)
            tokens = extract_tokens(post.title + " " + post.selftext)
            posts.append({
                "title": post.title,
                "url": post.url,
                "score": post.score,
                "created_utc": datetime.fromtimestamp(post.created_utc),
                "source": f"Reddit - r/{subreddit_name}",
                "upvote_ratio": post.upvote_ratio,
                "num_comments": post.num_comments,
                "sentiment": sentiment,
                "sentiment_score": score,
                "tokens": tokens
            })
        return posts
    except Exception as e:
        st.error(f"An error occurred while fetching posts from r/{subreddit_name}: {str(e)}")
        return []

def fetch_4chan_posts(board, limit=10):
    url = f"https://a.4cdn.org/{board}/catalog.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        posts = []
        data = response.json()
        for page in data:
            for thread in page['threads']:
                if 'com' in thread:
                    sentiment, score = analyze_sentiment(thread['com'])
                    tokens = extract_tokens(thread['com'])
                    posts.append({
                        "title": thread['com'][:100] + "...",
                        "url": f"https://boards.4chan.org/{board}/thread/{thread['no']}",
                        "score": thread.get('replies', 0),
                        "created_utc": datetime.fromtimestamp(thread['time']),
                        "source": f"4chan - /{board}/",
                        "sentiment": sentiment,
                        "sentiment_score": score,
                        "tokens": tokens
                    })
                if len(posts) >= limit:
                    break
            if len(posts) >= limit:
                break
        return posts[:limit]
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred while fetching posts from 4chan /{board}/: {str(e)}")
        return []

def get_coingecko_link(token):
    try:
        response = requests.get(f"https://api.coingecko.com/api/v3/search?query={token}")
        data = response.json()
        if data['coins']:
            return f"https://www.coingecko.com/en/coins/{data['coins'][0]['id']}"
    except:
        pass
    return None

def create_markdown_table(data):
    if not data:
        return "No data available"
    
    headers = data[0].keys()
    markdown = "| " + " | ".join(headers) + " |\n"
    markdown += "| " + " | ".join(["---" for _ in headers]) + " |\n"
    
    for row in data:
        markdown += "| " + " | ".join([str(row[col]) for col in headers]) + " |\n"
    
    return markdown

def evaluate_token(token_data):
    total_mentions = len(token_data['posts'])
    total_score = sum(post['score'] for post in token_data['posts'])
    avg_sentiment = token_data['avg_sentiment']
    
    # Criteria for a promising token
    min_mentions = 3
    min_total_score = 10
    min_avg_sentiment = 0.2
    
    is_promising = (
        total_mentions >= min_mentions and
        total_score >= min_total_score and
        avg_sentiment >= min_avg_sentiment
    )
    
    confidence_score = (
        (total_mentions / min_mentions) *
        (total_score / min_total_score) *
        (avg_sentiment / min_avg_sentiment)
    ) if is_promising else 0
    
    return is_promising, confidence_score

def main():
    st.title("Crypto Project Tracker with Smart Token Evaluation")

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

        if use_reddit and reddit is not None:
            reddit_subreddits = [
                "CryptoCurrency", "CryptoMarkets", "Altcoin", "Bitcoin", "Ethereum", "NFT",
                "CryptoMoonShots", "DeFi", "DefiDegens", "ethtrader", "Chainlink", "VeChain",
                "CryptoTechnology", "CryptoGems", "CryptoInvesting", "CryptoTraders",
                "cryptomoonshots", "cryptocommunity", "Crypto_Startup",
                "BitcoinBeginners", "Blockchain", "Crypto_Fraud", "ledger"
            ]
            for subreddit in reddit_subreddits:
                with st.spinner(f"Fetching posts from r/{subreddit}..."):
                    st.session_state.all_posts.extend(fetch_reddit_posts(subreddit))
                time.sleep(2)  # Add a delay to avoid hitting rate limits

        if use_4chan:
            chan_boards = ["biz", "g"]
            for board in chan_boards:
                with st.spinner(f"Fetching posts from 4chan /{board}/..."):
                    st.session_state.all_posts.extend(fetch_4chan_posts(board))

        # Sort posts by creation date
        st.session_state.all_posts.sort(key=lambda x: x['created_utc'], reverse=True)

        # Calculate weighted token sentiment scores
        token_sentiments = {}
        for post in st.session_state.all_posts:
            weight = post['score'] + 1  # Add 1 to avoid zero weights
            for token in post['tokens']:
                if token not in token_sentiments:
                    token_sentiments[token] = {'total_score': 0, 'total_weight': 0, 'posts': []}
                token_sentiments[token]['total_score'] += post['sentiment_score'] * weight
                token_sentiments[token]['total_weight'] += weight
                token_sentiments[token]['posts'].append(post)

        # Calculate weighted average sentiment and evaluate each token
        token_evaluations = {}
        for token, data in token_sentiments.items():
            avg_sentiment = data['total_score'] / data['total_weight']
            is_promising, confidence_score = evaluate_token({
                'avg_sentiment': avg_sentiment,
                'posts': data['posts']
            })
            token_evaluations[token] = {
                'avg_sentiment': avg_sentiment,
                'is_promising': is_promising,
                'confidence_score': confidence_score,
                'posts': sorted(data['posts'], key=lambda x: x['sentiment_score'], reverse=True)[:3]  # Top 3 posts by sentiment
            }

        # Sort tokens by confidence score
        sorted_tokens = sorted(token_evaluations.items(), key=lambda x: x[1]['confidence_score'], reverse=True)

        # Display top 20 promising tokens with links
        st.subheader("Top 20 Promising Tokens by Confidence Score")
        top_20_tokens = [token for token in sorted_tokens if token[1]['is_promising']][:20]
        token_data = []
        for token, data in top_20_tokens:
            post_links = " ".join([f"[Link {i+1}]({post['url']})" for i, post in enumerate(data['posts'][:3])])
            coingecko_link = get_coingecko_link(token)
            coingecko_text = f"[CoinGecko]({coingecko_link})" if coingecko_link else "N/A"
            token_data.append({
                'Token': token,
                'Confidence Score': f"{data['confidence_score']:.2f}",
                'Avg Sentiment': f"{data['avg_sentiment']:.2f}",
                'Mentions': len(data['posts']),
                'Top Posts': post_links,
                'CoinGecko': coingecko_text
            })
        
        markdown_table = create_markdown_table(token_data)
        st.markdown(markdown_table, unsafe_allow_html=True)

    # Display posts
    if st.session_state.all_posts:
        st.subheader("Latest Crypto Projects with Sentiment Analysis")
        df = pd.DataFrame(st.session_state.all_posts)
        
        # Add sentiment color coding
        def color_sentiment(val):
            if val == "Positive":
                return 'background-color: #90EE90'
            elif val == "Negative":
                return 'background-color: #FFA07A'
            else:
                return 'background-color: #F0F0F0'
        
        styled_df = df[['title', 'source', 'score', 'created_utc', 'sentiment']].style.applymap(color_sentiment, subset=['sentiment'])
        st.dataframe(styled_df)

        # Sentiment distribution
        st.subheader("Sentiment Distribution")
        sentiment_counts = df['sentiment'].value_counts()
        st.bar_chart(sentiment_counts)

        # Allow user to select a post to view details
        st.subheader("Post Details")
        selected_index = st.selectbox(
            "Select a post to view details:",
            options=range(len(st.session_state.all_posts)),
            format_func=lambda i: st.session_state.all_posts[i]['title'][:50] + "..."
        )

        if selected_index is not None:
            selected_post = st.session_state.all_posts[selected_index]
            st.markdown(f"**Title:** {selected_post['title']}")
            st.markdown(f"**Source:** {selected_post['source']}")
            st.markdown(f"**Score:** {selected_post['score']}")
            st.markdown(f"**Created:** {selected_post['created_utc']}")
            st.markdown(f"**Sentiment:** {selected_post['sentiment']} (Score: {selected_post['sentiment_score']:.2f})")
            if 'upvote_ratio' in selected_post:
                st.markdown(f"**Upvote Ratio:** {selected_post['upvote_ratio']:.2f}")
            if 'num_comments' in selected_post:
                st.markdown(f"**Number of Comments:** {selected_post['num_comments']}")
            st.markdown(f"**Tokens Mentioned:** {', '.join(selected_post['tokens'])}")
            st.markdown(f"**URL:** [{selected_post['url']}]({selected_post['url']})")

        # Token search and sentiment analysis
        st.subheader("Token Sentiment Analysis")
        token_name = st.text_input("Enter a token name to analyze sentiment:")
        if token_name:
            token_posts = [post for post in st.session_state.all_posts if token_name.upper() in post['tokens']]
            if token_posts:
                token_df = pd.DataFrame(token_posts)
                st.write(f"Posts mentioning {token_name}:")
                st.dataframe(token_df[['title', 'source', 'sentiment', 'sentiment_score']])
                
                avg_sentiment = token_df['sentiment_score'].mean()
                st.write(f"Average sentiment for {token_name}: {avg_sentiment:.2f}")
                
                if avg_sentiment > 0.05:
                    st.success(f"The overall sentiment for {token_name} is positive.")
                elif avg_sentiment < -0.05:
                    st.error(f"The overall sentiment for {token_name} is negative.")
                else:
                    st.info(f"The overall sentiment for {token_name} is neutral.")
                
                coingecko_link = get_coingecko_link(token_name)
                if coingecko_link:
                    st.markdown(f"[View {token_name} on CoinGecko]({coingecko_link})")
            else:
                st.warning(f"No posts found mentioning {token_name}.")

    else:
        st.warning("No posts fetched yet. Click 'Fetch New Crypto Projects' to load posts.")

if __name__ == "__main__":
    main()
