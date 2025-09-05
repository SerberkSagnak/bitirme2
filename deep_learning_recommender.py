
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Embedding, Flatten, Dot, Dense, Concatenate
from tensorflow.keras.optimizers import Adam
from sklearn.model_selection import train_test_split
import sqlite3

class DeepLearningRecommender:
    def __init__(self, num_users, num_movies, embedding_size=50):
        """
        Initializes the Deep Learning Recommender model.
        
        Args:
            num_users (int): Total number of unique users.
            num_movies (int): Total number of unique movies.
            embedding_size (int): The size of the embedding vectors.
        """
        self.num_users = num_users
        self.num_movies = num_movies
        self.embedding_size = embedding_size
        self.model = self._build_model()

    def _build_model(self):
        """
        Builds the Keras model architecture.
        """
        # User input layer
        user_id_input = Input(shape=[1], name='user_input')
        
        # Movie input layer
        movie_id_input = Input(shape=[1], name='movie_input')

        # User embedding layer
        user_embedding = Embedding(output_dim=self.embedding_size,
                                   input_dim=self.num_users,
                                   input_length=1,
                                   name='user_embedding')(user_id_input)
        
        # Movie embedding layer
        movie_embedding = Embedding(output_dim=self.embedding_size,
                                    input_dim=self.num_movies,
                                    input_length=1,
                                    name='movie_embedding')(movie_id_input)

        # Flatten the embedding layers
        user_vector = Flatten(name='flatten_user_vec')(user_embedding)
        movie_vector = Flatten(name='flatten_movie_vec')(movie_embedding)

        # Concatenate the flattened vectors
        concat = Concatenate()([user_vector, movie_vector])

        # Dense layers
        dense = Dense(128, activation='relu')(concat)
        dense = Dense(64, activation='relu')(dense)
        
        # Output layer
        output = Dense(1, activation='linear')(dense)

        model = Model(inputs=[user_id_input, movie_id_input], outputs=output)
        
        # Compile the model
        model.compile(optimizer=Adam(0.001), loss='mean_squared_error')
        
        return model

    def train(self, ratings_df, epochs=10, batch_size=64):
        """
        Trains the model on the provided ratings data.
        
        Args:
            ratings_df (pd.DataFrame): DataFrame containing user_id, movie_id, and rating.
            epochs (int): Number of epochs to train for.
            batch_size (int): Batch size for training.
        """
        # Prepare the data for training
        user_ids = ratings_df['user_id'].values
        movie_ids = ratings_df['movie_id'].values
        ratings = ratings_df['rating'].values

        # Split the data correctly
        user_ids_train, user_ids_val, movie_ids_train, movie_ids_val, ratings_train, ratings_val = train_test_split(
            user_ids, movie_ids, ratings, test_size=0.1, random_state=42
        )

        history = self.model.fit(
            x=[user_ids_train, movie_ids_train],
            y=ratings_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=([user_ids_val, movie_ids_val], ratings_val),
            verbose=1
        )
        return history

    def get_recommendations(self, user_id, all_movie_ids, n_recommendations=10):
        """
        Generates recommendations for a given user.
        
        Args:
            user_id (int): The ID of the user to get recommendations for.
            all_movie_ids (list): A list of all possible movie IDs.
            n_recommendations (int): The number of recommendations to return.
            
        Returns:
            list: A list of recommended movie IDs.
        """
        user_array = np.full(len(all_movie_ids), user_id)
        movie_array = np.array(all_movie_ids)
        
        predictions = self.model.predict([user_array, movie_array])
        
        # Create a DataFrame with predictions
        pred_df = pd.DataFrame({
            'movie_id': all_movie_ids,
            'predicted_rating': predictions.flatten()
        })
        
        # Sort by predicted rating and get top N
        top_n = pred_df.sort_values(by='predicted_rating', ascending=False).head(n_recommendations)
        
        return top_n
