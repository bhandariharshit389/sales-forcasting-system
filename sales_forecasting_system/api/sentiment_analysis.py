import pandas as pd
import numpy as np
from textblob import TextBlob
from collections import Counter
import re

class SentimentAnalyzer:
    def __init__(self):
        self.sentiment_mapping = {
            'positive': 1,
            'negative': -1,
            'neutral': 0
        }
    
    def analyze_reviews(self, df):
        """Perform sentiment analysis on review texts"""
        if 'reviews_text' not in df.columns:
            return {'error': 'No review text found'}
        
        df = df.copy()
        
        # Clean text
        df['clean_review'] = df['reviews_text'].apply(self._clean_text)
        
        # Get sentiment scores
        df['sentiment_score'] = df['clean_review'].apply(self._get_sentiment_score)
        
        # Categorize sentiment
        df['sentiment_category'] = df['sentiment_score'].apply(self._categorize_sentiment)
        
        # Aggregate results
        results = self._aggregate_results(df)
        
        return results
    
    def _clean_text(self, text):
        """Clean review text"""
        if pd.isna(text) or text == '':
            return ''
        
        # Convert to lowercase
        text = str(text).lower()
        
        # Remove special characters
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        
        # Remove extra spaces
        text = ' '.join(text.split())
        
        return text
    
    def _get_sentiment_score(self, text):
        """Get sentiment score using TextBlob"""
        if not text:
            return 0
        
        blob = TextBlob(text)
        return blob.sentiment.polarity
    
    def _categorize_sentiment(self, score):
        """Categorize sentiment based on score"""
        if score > 0.1:
            return 'positive'
        elif score < -0.1:
            return 'negative'
        else:
            return 'neutral'
    
    def _aggregate_results(self, df):
        """Aggregate sentiment analysis results"""
        sentiment_counts = df['sentiment_category'].value_counts().to_dict()
        
        # Calculate average sentiment by category
        avg_sentiment_by_category = df.groupby('product_category')['sentiment_score'].mean().to_dict()
        
        # Calculate average sentiment by rating
        avg_sentiment_by_rating = df.groupby('review_rating')['sentiment_score'].mean().to_dict()
        
        # Get most common positive/negative words
        all_positive_reviews = df[df['sentiment_category'] == 'positive']['clean_review'].str.cat(sep=' ')
        all_negative_reviews = df[df['sentiment_category'] == 'negative']['clean_review'].str.cat(sep=' ')
        
        positive_words = self._get_common_words(all_positive_reviews, top_n=10)
        negative_words = self._get_common_words(all_negative_reviews, top_n=10)
        
        return {
            'sentiment_distribution': sentiment_counts,
            'average_sentiment_score': df['sentiment_score'].mean(),
            'average_sentiment_by_category': avg_sentiment_by_category,
            'average_sentiment_by_rating': avg_sentiment_by_rating,
            'top_positive_words': positive_words,
            'top_negative_words': negative_words,
            'total_reviews': len(df),
            'positive_percentage': (sentiment_counts.get('positive', 0) / len(df)) * 100,
            'negative_percentage': (sentiment_counts.get('negative', 0) / len(df)) * 100,
            'neutral_percentage': (sentiment_counts.get('neutral', 0) / len(df)) * 100
        }
    
    def _get_common_words(self, text, top_n=10):
        """Get most common words from text"""
        if not text:
            return []
        
        # Split into words
        words = text.split()
        
        # Remove common stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                    'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
                    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us',
                    'them', 'my', 'your', 'his', 'her', 'our', 'their', 'too', 'very'}
        
        words = [word for word in words if word not in stopwords and len(word) > 2]
        
        # Count frequencies
        word_counts = Counter(words)
        
        return word_counts.most_common(top_n)