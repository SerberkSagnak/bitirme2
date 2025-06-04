import numpy as np
import pandas as pd
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score
import sqlite3
from datetime import datetime
import json
import random
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RecommendationMetrics:
    """Recommendation performance metrics"""
    algorithm: str
    precision: float
    recall: float
    f1_score: float
    coverage: float
    diversity: float
    novelty: float
    execution_time: float
    user_satisfaction: float = 0.0

class EnhancedHybridRecommender:
    """
    🚀 Enhanced Hybrid Recommendation System v6.1 (Fixed)
    """
    
    def __init__(self, db_path: str = 'movie_recommendation.db'):
        self.db_path = db_path
        self.user_movie_matrix = None
        self.movies_df = None
        self.users_df = None
        self.content_similarity_matrix = None
        self.svd_model = None
        self.performance_metrics = []
        self.ab_test_results = {}
        
        # Algorithm weights for hybrid approach
        self.algorithm_weights = {
            'collaborative_filtering': 0.35,
            'content_based': 0.25,
            'matrix_factorization': 0.25,
            'popularity_based': 0.15
        }
        
        logger.info("🚀 Enhanced Hybrid Recommender v6.1 initialized")

    def load_data(self):
        """Load all necessary data with enhanced error handling"""
        logger.info("📊 Loading system data...")
        
        try:
            # Load user-movie matrix
            with open('user_movie_matrix.pkl', 'rb') as f:
                self.user_movie_matrix = pickle.load(f)
            logger.info(f"✅ Matrix loaded: {self.user_movie_matrix.shape}")
        except Exception as e:
            logger.error(f"❌ Matrix loading failed: {e}")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Load movies with better genre handling
            movie_query = """
            SELECT movie_id, title, release_date, imdb_url, genres, 
                   COALESCE(avg_rating, 0.0) as avg_rating,
                   COALESCE(popularity_score, 0) as popularity
            FROM movies
            """
            self.movies_df = pd.read_sql_query(movie_query, conn)
            
            # Process genres field safely
            self.movies_df['genres_processed'] = self.movies_df['genres'].apply(self._process_genres)
            
            # Load users
            user_query = "SELECT id as user_id, username, email, age, gender, favorite_genres FROM users"
            self.users_df = pd.read_sql_query(user_query, conn)
            
            conn.close()
            logger.info(f"✅ Data loaded: {len(self.movies_df)} movies, {len(self.users_df)} users")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database loading failed: {e}")
            return False

    def _process_genres(self, genres_str):
        """Safely process genres string to list"""
        try:
            if pd.isna(genres_str) or not genres_str:
                return []
            
            # If it's already a list (from JSON)
            if isinstance(genres_str, list):
                return genres_str
            
            # If it's a JSON string
            if genres_str.startswith('[') and genres_str.endswith(']'):
                return json.loads(genres_str)
            
            # If it's pipe-separated
            if '|' in genres_str:
                return [g.strip() for g in genres_str.split('|')]
            
            # If it's comma-separated
            if ',' in genres_str:
                return [g.strip() for g in genres_str.split(',')]
            
            # Single genre
            return [genres_str.strip()]
            
        except Exception:
            return []

    def prepare_content_similarity(self):
        """Prepare content-based similarity matrix with better genre handling"""
        logger.info("🔄 Preparing content similarity matrix...")
        
        content_features = []
        for _, movie in self.movies_df.iterrows():
            # Use processed genres
            genres = ' '.join(movie['genres_processed']) if movie['genres_processed'] else ""
            year = str(movie['release_date'])[:4] if pd.notna(movie['release_date']) else ""
            content_features.append(f"{genres} {year}")
        
        # Calculate TF-IDF similarity
        tfidf = TfidfVectorizer(stop_words='english', max_features=1000)
        tfidf_matrix = tfidf.fit_transform(content_features)
        self.content_similarity_matrix = cosine_similarity(tfidf_matrix)
        
        logger.info("✅ Content similarity matrix prepared")

    def prepare_matrix_factorization(self, n_components: int = 50):
        """Prepare matrix factorization model"""
        logger.info("🔄 Preparing matrix factorization model...")
        
        # Fill NaN with 0 for SVD
        matrix_filled = self.user_movie_matrix.fillna(0)
        
        # Apply SVD
        self.svd_model = TruncatedSVD(n_components=n_components, random_state=42)
        self.svd_model.fit(matrix_filled)
        
        logger.info(f"✅ SVD model prepared with {n_components} components")

    def collaborative_filtering_recommendations(self, user_id: int, n_recommendations: int = 10) -> List[Tuple[int, float]]:
        """Enhanced Collaborative Filtering with better error handling"""
        start_time = datetime.now()
        
        try:
            if user_id not in self.user_movie_matrix.index:
                return []
            
            user_ratings = self.user_movie_matrix.loc[user_id]
            user_similarities = []
            
            for other_user in self.user_movie_matrix.index:
                if other_user != user_id:
                    other_ratings = self.user_movie_matrix.loc[other_user]
                    
                    common_movies = user_ratings.dropna().index.intersection(other_ratings.dropna().index)
                    if len(common_movies) > 3:  # Reduced threshold
                        try:
                            correlation = user_ratings[common_movies].corr(other_ratings[common_movies])
                            if not pd.isna(correlation) and correlation > 0:
                                user_similarities.append((other_user, correlation))
                        except:
                            continue
            
            if not user_similarities:
                return []
            
            user_similarities.sort(key=lambda x: x[1], reverse=True)
            
            recommendations = {}
            for similar_user, similarity in user_similarities[:5]:  # Top 5 similar users
                similar_user_ratings = self.user_movie_matrix.loc[similar_user]
                
                for movie_id, rating in similar_user_ratings.dropna().items():
                    if pd.isna(user_ratings[movie_id]) and rating >= 3.5:  # Lower threshold
                        if movie_id not in recommendations:
                            recommendations[movie_id] = 0
                        recommendations[movie_id] += similarity * rating
            
            sorted_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            logger.warning(f"CF Error for user {user_id}: {e}")
            return []
        
        execution_time = (datetime.now() - start_time).total_seconds()
        self._log_performance('collaborative_filtering', execution_time)
        
        return sorted_recs[:n_recommendations]

    def content_based_recommendations(self, user_id: int, n_recommendations: int = 10) -> List[Tuple[int, float]]:
        """Enhanced Content-based recommendations"""
        start_time = datetime.now()
        
        try:
            if user_id not in self.user_movie_matrix.index:
                return []
            
            user_ratings = self.user_movie_matrix.loc[user_id]
            liked_movies = user_ratings[user_ratings >= 3.5].index.tolist()  # Lower threshold
            
            if not liked_movies:
                return []
            
            content_scores = {}
            
            for liked_movie in liked_movies:
                try:
                    movie_idx = self.movies_df[self.movies_df['movie_id'] == liked_movie].index[0]
                    similarities = self.content_similarity_matrix[movie_idx]
                    
                    for idx, similarity in enumerate(similarities):
                        target_movie_id = self.movies_df.iloc[idx]['movie_id']
                        
                        if (target_movie_id not in liked_movies and 
                            pd.isna(user_ratings[target_movie_id]) and 
                            similarity > 0.1):  # Similarity threshold
                            
                            if target_movie_id not in content_scores:
                                content_scores[target_movie_id] = 0
                            content_scores[target_movie_id] += similarity
                            
                except (IndexError, KeyError):
                    continue
            
            sorted_recs = sorted(content_scores.items(), key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            logger.warning(f"Content-based Error for user {user_id}: {e}")
            return []
        
        execution_time = (datetime.now() - start_time).total_seconds()
        self._log_performance('content_based', execution_time)
        
        return sorted_recs[:n_recommendations]

    def matrix_factorization_recommendations(self, user_id: int, n_recommendations: int = 10) -> List[Tuple[int, float]]:
        """Enhanced Matrix Factorization recommendations"""
        start_time = datetime.now()
        
        try:
            if user_id not in self.user_movie_matrix.index:
                return []
            
            user_idx = list(self.user_movie_matrix.index).index(user_id)
            user_ratings = self.user_movie_matrix.loc[user_id]
            
            matrix_filled = self.user_movie_matrix.fillna(0)
            user_profile = matrix_filled.iloc[user_idx:user_idx+1]
            user_factors = self.svd_model.transform(user_profile)
            
            movie_factors = self.svd_model.components_
            predicted_ratings = np.dot(user_factors, movie_factors)[0]
            
            recommendations = []
            for movie_idx, movie_id in enumerate(self.user_movie_matrix.columns):
                if pd.isna(user_ratings[movie_id]):
                    predicted_rating = predicted_ratings[movie_idx]
                    if predicted_rating > 0:  # Only positive predictions
                        recommendations.append((movie_id, predicted_rating))
            
            recommendations.sort(key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            logger.warning(f"MF Error for user {user_id}: {e}")
            return []
        
        execution_time = (datetime.now() - start_time).total_seconds()
        self._log_performance('matrix_factorization', execution_time)
        
        return recommendations[:n_recommendations]

    def popularity_based_recommendations(self, user_id: int, n_recommendations: int = 10) -> List[Tuple[int, float]]:
        """Enhanced Popularity-based recommendations"""
        start_time = datetime.now()
        
        try:
            if user_id not in self.user_movie_matrix.index:
                return []
            
            user_ratings = self.user_movie_matrix.loc[user_id]
            
            # Get movies with good ratings and popularity
            popular_movies = self.movies_df[
                (self.movies_df['avg_rating'] >= 3.5) & 
                (self.movies_df['popularity'] > 0)
            ].nlargest(50, 'popularity')
            
            recommendations = []
            
            for _, movie in popular_movies.iterrows():
                movie_id = movie['movie_id']
                if pd.isna(user_ratings.get(movie_id, np.nan)):
                    popularity_score = movie['popularity'] * movie['avg_rating']
                    recommendations.append((movie_id, popularity_score))
            
            recommendations.sort(key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            logger.warning(f"Popularity Error for user {user_id}: {e}")
            return []
        
        execution_time = (datetime.now() - start_time).total_seconds()
        self._log_performance('popularity_based', execution_time)
        
        return recommendations[:n_recommendations]

    def hybrid_recommendations(self, user_id: int, n_recommendations: int = 10) -> List[Dict]:
        """Enhanced Hybrid Recommendations with better error handling"""
        logger.info(f"🎯 Generating hybrid recommendations for user {user_id}")
        
        # Get recommendations from all algorithms
        cf_recs = self.collaborative_filtering_recommendations(user_id, 20)
        content_recs = self.content_based_recommendations(user_id, 20)
        mf_recs = self.matrix_factorization_recommendations(user_id, 20)
        pop_recs = self.popularity_based_recommendations(user_id, 20)
        
        # Combine with weighted scoring
        combined_scores = {}
        
        # Collaborative Filtering
        for movie_id, score in cf_recs:
            combined_scores[movie_id] = combined_scores.get(movie_id, 0) + \
                                      score * self.algorithm_weights['collaborative_filtering']
        
        # Content-Based
        for movie_id, score in content_recs:
            combined_scores[movie_id] = combined_scores.get(movie_id, 0) + \
                                      score * self.algorithm_weights['content_based']
        
        # Matrix Factorization
        for movie_id, score in mf_recs:
            combined_scores[movie_id] = combined_scores.get(movie_id, 0) + \
                                      score * self.algorithm_weights['matrix_factorization']
        
        # Popularity-Based
        for movie_id, score in pop_recs:
            combined_scores[movie_id] = combined_scores.get(movie_id, 0) + \
                                      score * self.algorithm_weights['popularity_based']
        
        # Sort by combined score
        sorted_recommendations = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Enrich with movie details
        final_recommendations = []
        for movie_id, hybrid_score in sorted_recommendations[:n_recommendations]:
            try:
                movie_info = self.movies_df[self.movies_df['movie_id'] == movie_id].iloc[0]
                
                # Safe genre handling
                genres = movie_info['genres_processed'] if 'genres_processed' in movie_info else []
                genres_str = '|'.join(genres) if genres else "Unknown"
                
                recommendation = {
                    'movie_id': int(movie_id),
                    'title': str(movie_info['title']),
                    'genres': genres,  # Use processed genres list
                    'genres_str': genres_str,  # String version for display
                    'release_date': str(movie_info['release_date']) if pd.notna(movie_info['release_date']) else "Unknown",
                    'avg_rating': float(movie_info['avg_rating']) if pd.notna(movie_info['avg_rating']) else 0.0,
                    'popularity': int(movie_info['popularity']) if pd.notna(movie_info['popularity']) else 0,
                    'hybrid_score': float(hybrid_score),
                    'recommendation_method': 'Enhanced Hybrid v6.1',
                    'algorithm_breakdown': {
                        'cf_contribution': sum([score * self.algorithm_weights['collaborative_filtering']
                                              for mid, score in cf_recs if mid == movie_id]),
                        'content_contribution': sum([score * self.algorithm_weights['content_based']
                                                   for mid, score in content_recs if mid == movie_id]),
                        'mf_contribution': sum([score * self.algorithm_weights['matrix_factorization']
                                              for mid, score in mf_recs if mid == movie_id]),
                        'popularity_contribution': sum([score * self.algorithm_weights['popularity_based']
                                                      for mid, score in pop_recs if mid == movie_id])
                    }
                }
                final_recommendations.append(recommendation)
                
            except (IndexError, KeyError) as e:
                logger.warning(f"Error enriching movie {movie_id}: {e}")
                continue
        
        logger.info(f"✅ Generated {len(final_recommendations)} hybrid recommendations")
        return final_recommendations

    def evaluate_recommendations(self, test_user_id: int, recommendations: List[Dict],
                               actual_ratings: Dict[int, float]) -> RecommendationMetrics:
        """Enhanced evaluation with better handling"""
        start_time = datetime.now()
        
        try:
            # Extract recommended movie IDs
            recommended_movies = [rec['movie_id'] for rec in recommendations]
            
            # Filter actual ratings to only include movies in our dataset
            valid_actual_ratings = {mid: rating for mid, rating in actual_ratings.items() 
                                  if mid in self.movies_df['movie_id'].values}
            
            if not valid_actual_ratings:
                # If no valid ratings, use dummy metrics
                return RecommendationMetrics(
                    algorithm='hybrid_v6.1',
                    precision=0.0,
                    recall=0.0,
                    f1_score=0.0,
                    coverage=0.1,
                    diversity=0.5,
                    novelty=0.5,
                    execution_time=(datetime.now() - start_time).total_seconds()
                )
            
            # True Positives: Recommended movies that user actually liked (rating >= 4)
            true_positives = len([mid for mid in recommended_movies
                                if mid in valid_actual_ratings and valid_actual_ratings[mid] >= 4.0])
            
            # False Positives: Recommended movies that user didn't like (rating < 4)
            false_positives = len([mid for mid in recommended_movies
                                 if mid in valid_actual_ratings and valid_actual_ratings[mid] < 4.0])
            
            # False Negatives: Movies user liked but weren't recommended
            all_liked_movies = [mid for mid, rating in valid_actual_ratings.items() if rating >= 4.0]
            false_negatives = len([mid for mid in all_liked_movies if mid not in recommended_movies])
            
            # Calculate metrics with safe division
            precision = true_positives / len(recommended_movies) if recommended_movies else 0
            recall = true_positives / len(all_liked_movies) if all_liked_movies else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            # Coverage: Percentage of items in catalog that can be recommended
            total_movies = len(self.movies_df)
            coverage = len(set(recommended_movies)) / total_movies
            
            # Diversity: Genre diversity in recommendations
            genres_in_recs = set()
            for rec in recommendations:
                if rec.get('genres') and isinstance(rec['genres'], list):
                    genres_in_recs.update(rec['genres'])
            diversity = min(len(genres_in_recs) / 20, 1.0)  # Cap at 1.0
            
            # Novelty: Average inverse popularity
            novelty_scores = []
            for rec in recommendations:
                popularity = rec.get('popularity', 1)
                novelty_scores.append(1 / (popularity + 1))
            novelty = np.mean(novelty_scores) if novelty_scores else 0.5
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            metrics = RecommendationMetrics(
                algorithm='hybrid_v6.1',
                precision=precision,
                recall=recall,
                f1_score=f1,
                coverage=coverage,
                diversity=diversity,
                novelty=novelty,
                execution_time=execution_time
            )
            
            logger.info(f"📊 Evaluation completed: P={precision:.3f}, R={recall:.3f}, F1={f1:.3f}")
            return metrics
            
        except Exception as e:
            logger.error(f"Evaluation error: {e}")
            return RecommendationMetrics(
                algorithm='hybrid_v6.1',
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                coverage=0.0,
                diversity=0.0,
                novelty=0.0,
                execution_time=(datetime.now() - start_time).total_seconds()
            )

    def ab_test_algorithms(self, test_users: List[int], n_recommendations: int = 10) -> Dict:
        """Enhanced A/B Testing with better error handling"""
        logger.info(f"🧪 Starting A/B test with {len(test_users)} users")
        
        algorithms = {
            'hybrid_v6': self.hybrid_recommendations,
            'collaborative_filtering': self._wrap_algorithm_for_testing(self.collaborative_filtering_recommendations),
            'content_based': self._wrap_algorithm_for_testing(self.content_based_recommendations),
            'matrix_factorization': self._wrap_algorithm_for_testing(self.matrix_factorization_recommendations),
            'popularity_based': self._wrap_algorithm_for_testing(self.popularity_based_recommendations)
        }
        
        results = {}
        
        for algorithm_name, algorithm_func in algorithms.items():
            logger.info(f"🔄 Testing {algorithm_name}...")
            
            algorithm_metrics = []
            
            for user_id in test_users:
                try:
                    # Get recommendations
                    recommendations = algorithm_func(user_id, n_recommendations)
                    
                    if not recommendations:
                        continue
                    
                    # Get user's actual ratings for evaluation
                    if user_id in self.user_movie_matrix.index:
                        user_ratings = self.user_movie_matrix.loc[user_id].dropna().to_dict()
                    else:
                        user_ratings = {}
                    
                    # Evaluate
                    metrics = self.evaluate_recommendations(user_id, recommendations, user_ratings)
                    algorithm_metrics.append(metrics)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error testing {algorithm_name} for user {user_id}: {e}")
                    continue
            
            # Aggregate metrics
            if algorithm_metrics:
                avg_precision = np.mean([m.precision for m in algorithm_metrics])
                avg_recall = np.mean([m.recall for m in algorithm_metrics])
                avg_f1 = np.mean([m.f1_score for m in algorithm_metrics])
                avg_coverage = np.mean([m.coverage for m in algorithm_metrics])
                avg_diversity = np.mean([m.diversity for m in algorithm_metrics])
                avg_novelty = np.mean([m.novelty for m in algorithm_metrics])
                avg_execution_time = np.mean([m.execution_time for m in algorithm_metrics])
                
                results[algorithm_name] = {
                    'precision': avg_precision,
                    'recall': avg_recall,
                    'f1_score': avg_f1,
                    'coverage': avg_coverage,
                    'diversity': avg_diversity,
                    'novelty': avg_novelty,
                    'execution_time': avg_execution_time,
                    'test_users': len(algorithm_metrics)
                }
            else:
                results[algorithm_name] = {
                    'precision': 0.0,
                    'recall': 0.0,
                    'f1_score': 0.0,
                    'coverage': 0.0,
                    'diversity': 0.0,
                    'novelty': 0.0,
                    'execution_time': 0.0,
                    'test_users': 0
                }
        
        self.ab_test_results = results
        logger.info("✅ A/B testing completed")
        return results

    def _wrap_algorithm_for_testing(self, algorithm_func):
        """Wrap single algorithm functions to return proper format for testing"""
        def wrapper(user_id: int, n_recommendations: int = 10):
            try:
                recs = algorithm_func(user_id, n_recommendations)
                formatted_recs = []
                
                for movie_id, score in recs:
                    try:
                        movie_info = self.movies_df[self.movies_df['movie_id'] == movie_id].iloc[0]
                        
                        # Safe genre handling
                        genres = movie_info['genres_processed'] if 'genres_processed' in movie_info else []
                        
                        rec = {
                            'movie_id': int(movie_id),
                            'title': str(movie_info['title']),
                            'genres': genres,
                            'hybrid_score': float(score),
                            'avg_rating': float(movie_info['avg_rating']) if pd.notna(movie_info['avg_rating']) else 0.0,
                            'popularity': int(movie_info['popularity']) if pd.notna(movie_info['popularity']) else 0
                        }
                        formatted_recs.append(rec)
                    except (IndexError, KeyError):
                        continue
                
                return formatted_recs
            except Exception as e:
                logger.warning(f"Algorithm wrapper error: {e}")
                return []
        
        return wrapper

    def get_performance_analytics(self) -> Dict:
        """Enhanced analytics with better data handling"""
        try:
            total_ratings = self.user_movie_matrix.count().sum()
            matrix_size = self.user_movie_matrix.size
            sparsity = (self.user_movie_matrix.isnull().sum().sum() / matrix_size) * 100
            
            analytics = {
                'system_overview': {
                    'total_users': len(self.users_df) if self.users_df is not None else 0,
                    'total_movies': len(self.movies_df) if self.movies_df is not None else 0,
                    'total_ratings': int(total_ratings),
                    'matrix_sparsity': round(sparsity, 2),
                    'system_version': 'Enhanced Hybrid v6.1'
                },
                'algorithm_weights': self.algorithm_weights,
                'recent_performance': self.performance_metrics[-50:] if self.performance_metrics else [],
                'ab_test_results': self.ab_test_results,
                'recommendation_quality': {
                    'avg_precision': np.mean([m.precision for m in self.performance_metrics[-20:]]) if len(self.performance_metrics) >= 20 else 0,
                    'avg_recall': np.mean([m.recall for m in self.performance_metrics[-20:]]) if len(self.performance_metrics) >= 20 else 0,
                    'avg_f1_score': np.mean([m.f1_score for m in self.performance_metrics[-20:]]) if len(self.performance_metrics) >= 20 else 0
                }
            }
            
            return analytics
        except Exception as e:
            logger.error(f"Analytics generation error: {e}")
            return {'error': str(e)}

    def optimize_algorithm_weights(self, test_users: List[int]):
        """Enhanced weight optimization"""
        logger.info("🎯 Optimizing algorithm weights...")
        
        best_weights = self.algorithm_weights.copy()
        best_f1_score = 0
        
        # Try different weight combinations
        weight_combinations = [
            {'collaborative_filtering': 0.4, 'content_based': 0.3, 'matrix_factorization': 0.2, 'popularity_based': 0.1},
            {'collaborative_filtering': 0.3, 'content_based': 0.4, 'matrix_factorization': 0.2, 'popularity_based': 0.1},
                        {'collaborative_filtering': 0.3, 'content_based': 0.2, 'matrix_factorization': 0.4, 'popularity_based': 0.1},
            {'collaborative_filtering': 0.2, 'content_based': 0.2, 'matrix_factorization': 0.3, 'popularity_based': 0.3},
            {'collaborative_filtering': 0.5, 'content_based': 0.2, 'matrix_factorization': 0.2, 'popularity_based': 0.1}
        ]
        
        for weights in weight_combinations:
            self.algorithm_weights = weights
            
            total_f1 = 0
            valid_tests = 0
            
            for user_id in test_users:
                try:
                    recommendations = self.hybrid_recommendations(user_id, 10)
                    if not recommendations:
                        continue
                    
                    if user_id in self.user_movie_matrix.index:
                        user_ratings = self.user_movie_matrix.loc[user_id].dropna().to_dict()
                    else:
                        user_ratings = {}
                    
                    metrics = self.evaluate_recommendations(user_id, recommendations, user_ratings)
                    total_f1 += metrics.f1_score
                    valid_tests += 1
                except:
                    continue
            
            avg_f1 = total_f1 / valid_tests if valid_tests > 0 else 0
            
            if avg_f1 > best_f1_score:
                best_f1_score = avg_f1
                best_weights = weights.copy()
        
        self.algorithm_weights = best_weights
        logger.info(f"✅ Optimized weights: {best_weights}, F1: {best_f1_score:.3f}")

    def _log_performance(self, algorithm: str, execution_time: float):
        """Log performance metrics"""
        metric = RecommendationMetrics(
            algorithm=algorithm,
            precision=0,  # Will be filled by evaluation
            recall=0,
            f1_score=0,
            coverage=0,
            diversity=0,
            novelty=0,
            execution_time=execution_time
        )
        self.performance_metrics.append(metric)

    def validate_system_requirements(self):
        """Sistem gereksinimlerini kontrol et"""
        logger.info("🔍 Validating system requirements...")
        
        try:
            import os
            if not os.path.exists('user_movie_matrix.pkl'):
                logger.error("❌ user_movie_matrix.pkl file not found!")
                return False
        except Exception as e:
            logger.error(f"❌ File check failed: {e}")
            return False
        
        try:
            if not os.path.exists(self.db_path):
                logger.error(f"❌ Database file {self.db_path} not found!")
                return False
        except Exception as e:
            logger.error(f"❌ Database check failed: {e}")
            return False
        
        logger.info("✅ System requirements validated")
        return True

    def initialize_system(self):
        """🚀 Complete System Initialization"""
        logger.info("🚀 Initializing Enhanced Hybrid Recommendation System v6.1")
        
        if not self.validate_system_requirements():
            logger.error("❌ System requirements validation failed!")
            return False
        
        if not self.load_data():
            logger.error("❌ System initialization failed!")
            return False
        
        self.prepare_content_similarity()
        self.prepare_matrix_factorization()
        
        logger.info("✅ System initialization completed!")
        return True

# 🔧 ENHANCED FASTAPI INTEGRATION
class EnhancedRecommendationAPI:
    """FastAPI integration for Enhanced Hybrid Recommender"""
    
    def __init__(self):
        self.recommender = EnhancedHybridRecommender()
        self.is_initialized = False

    async def initialize(self):
        """Initialize the recommendation system"""
        if not self.is_initialized:
            success = self.recommender.initialize_system()
            self.is_initialized = success
            return success
        return True

    async def get_hybrid_recommendations(self, user_id: int, n_recommendations: int = 10):
        """Get hybrid recommendations for a user"""
        if not await self.initialize():
            raise Exception("System not initialized")
        
        return self.recommender.hybrid_recommendations(user_id, n_recommendations)

    async def get_performance_analytics(self):
        """Get system performance analytics"""
        if not await self.initialize():
            raise Exception("System not initialized")
        
        return self.recommender.get_performance_analytics()

    async def run_ab_test(self, test_users: List[int]):
        """Run A/B test comparison"""
        if not await self.initialize():
            raise Exception("System not initialized")
        
        return self.recommender.ab_test_algorithms(test_users)

def create_sample_data_if_needed():
    """Eğer gerekli dosyalar yoksa örnek veri oluştur"""
    import os
    
    if not os.path.exists('user_movie_matrix.pkl'):
        logger.warning("⚠️ user_movie_matrix.pkl not found, creating sample data...")
        
        # Örnek user-movie matrix oluştur
        np.random.seed(42)
        sample_matrix = pd.DataFrame(
            np.random.choice([np.nan, 1, 2, 3, 4, 5], size=(100, 50), p=[0.9, 0.02, 0.02, 0.02, 0.02, 0.02]),
            index=range(1, 101),  # user_id 1-100
            columns=range(1, 51)  # movie_id 1-50
        )
        
        with open('user_movie_matrix.pkl', 'wb') as f:
            pickle.dump(sample_matrix, f)
        
        logger.info("✅ Sample user_movie_matrix.pkl created")

def create_test_data():
    """Create more realistic test data with actual user preferences"""
    logger.info("🔧 Creating enhanced test data...")
    
    try:
        # Connect to database to get real movie IDs
        conn = sqlite3.connect('movie_recommendation.db')
        movies_df = pd.read_sql_query("SELECT movie_id FROM movies LIMIT 100", conn)
        users_df = pd.read_sql_query("SELECT id FROM users LIMIT 50", conn)
        conn.close()
        
        if len(movies_df) == 0 or len(users_df) == 0:
            logger.warning("No data in database, using sample IDs")
            movie_ids = list(range(1, 101))
            user_ids = list(range(1, 51))
        else:
            movie_ids = movies_df['movie_id'].head(100).tolist()
            user_ids = users_df['id'].head(50).tolist()
        
        # Create more realistic rating patterns
        np.random.seed(42)
        matrix_data = {}
        
        for user_id in user_ids:
            user_ratings = {}
            # Each user rates 10-30 movies with preference patterns
            n_ratings = np.random.randint(10, 31)
            rated_movies = np.random.choice(movie_ids, n_ratings, replace=False)
            
            for movie_id in rated_movies:
                # More realistic rating distribution
                rating = np.random.choice([1, 2, 3, 4, 5], p=[0.1, 0.1, 0.2, 0.4, 0.2])
                user_ratings[movie_id] = rating
            
            matrix_data[user_id] = user_ratings
        
        # Convert to DataFrame
        rating_matrix = pd.DataFrame(matrix_data).T
        rating_matrix = rating_matrix.reindex(columns=movie_ids)
        
        # Save enhanced matrix
        with open('user_movie_matrix.pkl', 'wb') as f:
            pickle.dump(rating_matrix, f)
        
        logger.info(f"✅ Enhanced test data created: {len(user_ids)} users, {len(movie_ids)} movies")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test data creation failed: {e}")
        return False

def test_enhanced_system():
    """🧪 ENHANCED SYSTEM TESTING"""
    logger.info("🧪 Testing Enhanced Hybrid Recommendation System v6.1")
    
    # Create enhanced test data if needed
    if not create_test_data():
        create_sample_data_if_needed()
    
    # Initialize system
    recommender = EnhancedHybridRecommender()
    if not recommender.initialize_system():
        logger.error("❌ System initialization failed!")
        return
    
    # Test with sample users
    test_users = list(recommender.user_movie_matrix.index[:5])
    logger.info(f"Testing with users: {test_users}")
    
    print("\n" + "="*80)
    print("🎯 ENHANCED HYBRID RECOMMENDATION SYSTEM v6.1 TEST RESULTS")
    print("="*80)
    
    # Test individual recommendations
    for user_id in test_users:
        print(f"\n📊 Hybrid Recommendations for User {user_id}:")
        print("-" * 60)
        
        try:
            recommendations = recommender.hybrid_recommendations(user_id, 5)
            
            if recommendations:
                for i, rec in enumerate(recommendations, 1):
                    print(f"{i}. {rec['title']}")
                    print(f"   📊 Score: {rec['hybrid_score']:.3f}")
                    print(f"   🎭 Genres: {rec['genres_str']}")
                    print(f"   ⭐ Rating: {rec['avg_rating']:.1f} | 👥 Popularity: {rec['popularity']}")
                    
                    breakdown = rec['algorithm_breakdown']
                    print(f"   🔬 Algorithm Breakdown:")
                    print(f"      CF: {breakdown['cf_contribution']:.2f} | "
                          f"Content: {breakdown['content_contribution']:.2f} | "
                          f"MF: {breakdown['mf_contribution']:.2f} | "
                          f"Pop: {breakdown['popularity_contribution']:.2f}")
                    print()
            else:
                print("   ❌ No recommendations generated")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Run A/B test
    print("\n" + "="*80)
    print("🧪 A/B TEST RESULTS")
    print("="*80)
    
    try:
        ab_results = recommender.ab_test_algorithms(test_users)
        
        for algorithm, metrics in ab_results.items():
            print(f"\n📊 {algorithm.upper().replace('_', ' ')}:")
            print(f"   Precision: {metrics['precision']:.3f}")
            print(f"   Recall: {metrics['recall']:.3f}")
            print(f"   F1-Score: {metrics['f1_score']:.3f}")
            print(f"   Coverage: {metrics['coverage']:.3f}")
            print(f"   Diversity: {metrics['diversity']:.3f}")
            print(f"   Novelty: {metrics['novelty']:.3f}")
            print(f"   Execution Time: {metrics['execution_time']:.3f}s")
            print(f"   Test Users: {metrics['test_users']}")
            
    except Exception as e:
        print(f"❌ A/B Test Error: {e}")
    
    # Get performance analytics
    print("\n" + "="*80)
    print("📊 SYSTEM ANALYTICS")
    print("="*80)
    
    try:
        analytics = recommender.get_performance_analytics()
        
        if 'system_overview' in analytics:
            overview = analytics['system_overview']
            print(f"\n🔢 System Overview:")
            print(f"   Total Users: {overview['total_users']:,}")
            print(f"   Total Movies: {overview['total_movies']:,}")
            print(f"   Total Ratings: {overview['total_ratings']:,}")
            print(f"   Matrix Sparsity: {overview['matrix_sparsity']:.1f}%")
            print(f"   System Version: {overview['system_version']}")
        
        if 'algorithm_weights' in analytics:
            print(f"\n⚖️ Algorithm Weights:")
            for algo, weight in analytics['algorithm_weights'].items():
                print(f"   {algo.replace('_', ' ').title()}: {weight:.2f}")
                
    except Exception as e:
        print(f"❌ Analytics Error: {e}")
    
    # Test algorithm weight optimization
    print("\n" + "="*80)
    print("🎯 ALGORITHM WEIGHT OPTIMIZATION")
    print("="*80)
    
    try:
        original_weights = recommender.algorithm_weights.copy()
        print(f"Original weights: {original_weights}")
        
        recommender.optimize_algorithm_weights(test_users)
        
        optimized_weights = recommender.algorithm_weights
        print(f"Optimized weights: {optimized_weights}")
        
        # Show improvement
        improvements = {}
        for algo in original_weights:
            change = optimized_weights[algo] - original_weights[algo]
            improvements[algo] = change
        
        print("\n📈 Weight Changes:")
        for algo, change in improvements.items():
            direction = "↗️" if change > 0 else "↘️" if change < 0 else "➡️"
            print(f"   {algo.replace('_', ' ').title()}: {change:+.3f} {direction}")
            
    except Exception as e:
        print(f"❌ Optimization Error: {e}")
    
    print("\n" + "="*80)
    print("✅ ENHANCED SYSTEM TESTING COMPLETED!")
    print("="*80)

if __name__ == "__main__":
    test_enhanced_system()

