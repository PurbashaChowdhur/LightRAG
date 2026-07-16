import matplotlib.pyplot as plt
import argparse
import logging
import os
import pandas as pd
from src.utils._io import *
from collections import Counter

class Stats():
    def __init__(
            self,
            data_dir: str,
            output_dir: str,
            logger: logging.Logger = logging.getLogger(__name__)
    ):
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.logger = logger

    def plot_chunk_length_distribution(self):
        total_chunks = 0
        chunk_lengths = []

        for i in range(1,14):
            chapter = load_from_pkl(os.path.join(self.data_dir, f"chapters/chapter_{i}.pkl"))
            if chapter.sections == []:
                for article in chapter.articles:
                    for _, chunk in enumerate(article.chunks):
                        total_chunks += 1
                        chunk_lengths.append(len(chunk.chunk_content))
            else:
                for section in chapter.sections:
                    for article in section.articles:
                        for _, chunk in enumerate(article.chunks):
                            total_chunks += 1
                            chunk_lengths.append(len(chunk.chunk_content))

        average_chunk_length = sum(chunk_lengths) / total_chunks if total_chunks > 0 else 0
        max_chunk_length = max(chunk_lengths) if chunk_lengths else 0
        min_chunk_length = min(chunk_lengths) if chunk_lengths else 0

        self.logger.info(f"Total chunks: {total_chunks}")
        self.logger.info(f"Average chunk length: {average_chunk_length}")
        self.logger.info(f"Max chunk length: {max_chunk_length}")
        self.logger.info(f"Min chunk length: {min_chunk_length}")

        plt.figure(figsize=(10, 6))
        plt.hist(chunk_lengths, bins=30, edgecolor='black')
        plt.title('Distribution of Chunk Lengths')
        plt.xlabel('Chunk Length (number of words)')
        plt.ylabel('Frequency')
        plt.savefig(f'{self.output_dir}/chunk_length_distribution.png')

        self.logger.info(f"Chunk length distribution plot saved to {self.output_dir}/chunk_length_distribution.png")

    def plot_chunk_count(self):
        chunk_counts = []

        for i in range(1, 14):
            chapter = load_from_pkl(os.path.join(self.data_dir, f"chapters/chapter_{i}.pkl"))
            if chapter.sections == []:
                for article in chapter.articles:
                    chunk_count = len(article.chunks)
                    chunk_counts.append(chunk_count)
            else:
                for section in chapter.sections:
                    for article in section.articles:
                        chunk_count = len(article.chunks)
                        chunk_counts.append(chunk_count)

        chunk_count_freq = Counter(chunk_counts)
        chunk_count_values = list(chunk_count_freq.keys())
        frequencies = list(chunk_count_freq.values())

        average_chunks_per_article = sum(chunk_counts) / len(chunk_counts) if len(chunk_counts) > 0 else 0
        self.logger.info(f"Average number of chunks per article: {average_chunks_per_article}")

        plt.figure(figsize=(12, 6))
        plt.bar(chunk_count_values, frequencies, color='steelblue')
        plt.xlabel('Number of Chunks per Article')
        plt.ylabel('Frequency')
        plt.title('Frequency of Number of Chunks per Article')
        plt.xticks(rotation=90)
        plt.savefig(f'{self.output_dir}/chunk_count.png')

        self.logger.info(f"Chunk count plot saved to {self.output_dir}/chunk_count.png")

    def plot_most_referred(self, entity:str):
        match entity:
            case 'Article':
                data = self.db.query("""
                        MATCH (a:Article) 
                        RETURN a.id AS entity_id, count{(a)<-[:HAS_REFERENCE]-()} AS number_of_connections
                        ORDER BY number_of_connections DESC LIMIT 15
                        """)
                
            case 'Annex':
                data = self.db.query("""
                        MATCH (a:Annex) 
                        RETURN a.id AS entity_id, count{(a)<-[:HAS_REFERENCE]-()} AS number_of_connections
                        ORDER BY number_of_connections DESC LIMIT 15
                        """)

        df = pd.DataFrame.from_records(data, columns=['entity_id', 'number_of_connections'])
        df.plot(kind='bar', x='entity_id', y='number_of_connections', legend=False, figsize=(15, 10), color='steelblue')

        plt.xlabel(f'{entity}')
        plt.ylabel('Number of References')
        plt.title(f'Top 30 {entity}s by Number of References')
        plt.xticks()
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/most_referred_{entity}.png')

        self.logger.info(f"Most referred {entity} plot saved to {self.output_dir}/most_referred_{entity}.png")

    def plot_most_mentioned_key_element(self):
        data = self.db.query("""
                        MATCH (a:KeyElement) 
                        RETURN a.content AS key_element, count{(a)<-[:HAS_KEY_ELEMENT]-()} AS number_of_connections
                        ORDER BY number_of_connections DESC LIMIT 15
                        """)

        df = pd.DataFrame.from_records(data, columns=['key_element', 'number_of_connections'])

        df['key_element'] = df['key_element'].str.capitalize()
        df = df.sort_values(by='number_of_connections', ascending=False)
        colors = ['orange' if i < 4 else 'steelblue' for i in range(len(df))]

        plt.figure(figsize=(13, 8))
        bars = plt.bar(df['key_element'], df['number_of_connections'], color=colors)

        plt.xlabel('Key Element', fontsize=14)
        plt.ylabel('Number of References', fontsize=14)
        plt.title('Top 15 Key Elements by Number of References', fontsize=14, fontweight='bold')
        plt.xticks(rotation=45, ha='right', fontsize=12)  
        plt.grid(axis='y', linestyle='--', alpha=0.7)  

        for bar in bars:
            plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    str(bar.get_height()), ha='center', va='bottom', fontsize=12)

        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/most_mentioned_key_element.png')

        self.logger.info(f"Most mentioned key element plot saved to {self.output_dir}/most_mentioned_key_element.png")

def main(args: argparse.Namespace):
    logging.basicConfig(level=logging.INFO)

    stats = Stats(args.data_dir, args.output_dir)
    stats.plot_chunk_length_distribution()
    stats.plot_chunk_count()
    stats.plot_most_referred('Article')
    stats.plot_most_referred('Annex')
    stats.plot_most_mentioned_key_element()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--data_dir', type=str, default='data/ai act')
    parser.add_argument('--output_dir', type=str, default='figures')

    args = parser.parse_args()
    main(args)