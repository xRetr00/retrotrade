import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from textblob import TextBlob
from transformers import pipeline
import tweepy
import praw
import requests
import logging
import yaml
import json
from datetime import datetime, timedelta

class SentimentAnalyzer:
    def __init__(self, config_path: str = '../config/config.yaml'):
        """Initialize the sentiment analyzer."""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        self.logger = logging.getLogger('SentimentAnalyzer')
        
        # Initialize sentiment pipeline
        self.sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="finiteautomata/bertweet-base-sentiment-analysis"
        )
        
        # Initialize social media APIs
        self._init_twitter_api()
        self._init_reddit_api()
        self._init_news_api()
    
    def _init_twitter_api(self):
        """Initialize Twitter API."""
        try:
            auth = tweepy.OAuthHandler(
                self.config['twitter']['api_key'],
                self.config['twitter']['api_secret']
            )
            auth.set_access_token(
                self.config['twitter']['access_token'],
                self.config['twitter']['access_token_secret']
            )
            self.twitter_api = tweepy.API(auth)
        except Exception as e:
            self.logger.error(f"Error initializing Twitter API: {str(e)}")
            self.twitter_api = None
    
    def _init_reddit_api(self):
        """Initialize Reddit API."""
        try:
            self.reddit_api = praw.Reddit(
                client_id=self.config['reddit']['client_id'],
                client_secret=self.config['reddit']['client_secret'],
                user_agent=self.config['reddit']['user_agent']
            )
        except Exception as e:
            self.logger.error(f"Error initializing Reddit API: {str(e)}")
            self.reddit_api = None
    
    def _init_news_api(self):
        """Initialize News API."""
        self.news_api_key = self.config['news']['api_key']
    
    def get_twitter_sentiment(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get sentiment from Twitter posts."""
        try:
            if not self.twitter_api:
                return []
            
            # Search for tweets
            query = f"#{symbol} OR ${symbol} -filter:retweets"
            tweets = self.twitter_api.search_tweets(
                q=query,
                lang="en",
                count=limit,
                tweet_mode="extended"
            )
            
            # Analyze sentiment
            sentiments = []
            for tweet in tweets:
                text = tweet.full_text
                sentiment = self.sentiment_pipeline(text)[0]
                
                sentiments.append({
                    'source': 'twitter',
                    'text': text,
                    'sentiment': sentiment['label'],
                    'score': sentiment['score'],
                    'timestamp': tweet.created_at
                })
            
            return sentiments
        
        except Exception as e:
            self.logger.error(f"Error getting Twitter sentiment: {str(e)}")
            return []
    
    def get_reddit_sentiment(self, subreddits: List[str] = ['cryptocurrency', 'bitcoin', 'wallstreetbets'],
                           limit: int = 100) -> List[Dict]:
        """Get sentiment from Reddit posts."""
        try:
            if not self.reddit_api:
                return []
            
            sentiments = []
            for subreddit_name in subreddits:
                subreddit = self.reddit_api.subreddit(subreddit_name)
                
                # Get hot posts
                for post in subreddit.hot(limit=limit):
                    text = f"{post.title} {post.selftext}"
                    sentiment = self.sentiment_pipeline(text)[0]
                    
                    sentiments.append({
                        'source': 'reddit',
                        'text': text,
                        'sentiment': sentiment['label'],
                        'score': sentiment['score'],
                        'timestamp': datetime.fromtimestamp(post.created_utc)
                    })
            
            return sentiments
        
        except Exception as e:
            self.logger.error(f"Error getting Reddit sentiment: {str(e)}")
            return []
    
    def get_news_sentiment(self, symbol: str) -> List[Dict]:
        """Get sentiment from news articles."""
        try:
            # Get news articles
            url = f"https://newsapi.org/v2/everything"
            params = {
                'q': symbol,
                'apiKey': self.news_api_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'from': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            }
            
            response = requests.get(url, params=params)
            articles = response.json().get('articles', [])
            
            # Analyze sentiment
            sentiments = []
            for article in articles:
                text = f"{article['title']} {article['description']}"
                sentiment = self.sentiment_pipeline(text)[0]
                
                sentiments.append({
                    'source': 'news',
                    'text': text,
                    'sentiment': sentiment['label'],
                    'score': sentiment['score'],
                    'timestamp': datetime.strptime(article['publishedAt'], '%Y-%m-%dT%H:%M:%SZ')
                })
            
            return sentiments
        
        except Exception as e:
            self.logger.error(f"Error getting news sentiment: {str(e)}")
            return []
    
    def analyze_overall_sentiment(self, symbol: str) -> Tuple[float, Dict]:
        """Analyze overall sentiment from all sources."""
        try:
            # Collect sentiments from all sources
            twitter_sentiments = self.get_twitter_sentiment(symbol)
            reddit_sentiments = self.get_reddit_sentiment()
            news_sentiments = self.get_news_sentiment(symbol)
            
            all_sentiments = twitter_sentiments + reddit_sentiments + news_sentiments
            
            if not all_sentiments:
                return 0.0, {}
            
            # Calculate sentiment metrics
            sentiment_scores = []
            source_metrics = {
                'twitter': {'positive': 0, 'negative': 0, 'neutral': 0},
                'reddit': {'positive': 0, 'negative': 0, 'neutral': 0},
                'news': {'positive': 0, 'negative': 0, 'neutral': 0}
            }
            
            for item in all_sentiments:
                # Convert sentiment to score (-1 to 1)
                if item['sentiment'] == 'positive':
                    score = item['score']
                    sentiment_scores.append(score)
                    source_metrics[item['source']]['positive'] += 1
                elif item['sentiment'] == 'negative':
                    score = -item['score']
                    sentiment_scores.append(score)
                    source_metrics[item['source']]['negative'] += 1
                else:
                    score = 0
                    sentiment_scores.append(score)
                    source_metrics[item['source']]['neutral'] += 1
            
            # Calculate overall sentiment score (-1 to 1)
            overall_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0.0
            
            # Calculate source-wise sentiment ratios
            metrics = {}
            for source, counts in source_metrics.items():
                total = sum(counts.values())
                if total > 0:
                    metrics[source] = {
                        'positive_ratio': counts['positive'] / total,
                        'negative_ratio': counts['negative'] / total,
                        'neutral_ratio': counts['neutral'] / total,
                        'total_posts': total
                    }
            
            return overall_sentiment, metrics
        
        except Exception as e:
            self.logger.error(f"Error analyzing overall sentiment: {str(e)}")
            return 0.0, {}
    
    def get_sentiment_signal(self, symbol: str) -> Tuple[int, float]:
        """Get trading signal based on sentiment analysis."""
        try:
            # Get overall sentiment
            sentiment_score, metrics = self.analyze_overall_sentiment(symbol)
            
            # Convert sentiment to signal
            if abs(sentiment_score) < 0.2:  # Neutral zone
                signal = 0
                confidence = abs(sentiment_score) * 5  # Scale to 0-1
            else:
                signal = 1 if sentiment_score > 0 else -1
                confidence = abs(sentiment_score)
            
            return signal, confidence
        
        except Exception as e:
            self.logger.error(f"Error getting sentiment signal: {str(e)}")
            return 0, 0.0

if __name__ == "__main__":
    # Example usage
    analyzer = SentimentAnalyzer()
    signal, confidence = analyzer.get_sentiment_signal("BTC")
    print(f"Sentiment signal: {signal}, Confidence: {confidence:.2f}") 