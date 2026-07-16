import sys
import os
import argparse
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils._io import *
from settings.global_variables import *
from src.datamodule.act import *
from src.datamodule.gr_base import *
from tqdm import tqdm
from logging import Logger

class DataLoader():
    def __init__(
            self, 
            target_dir:str,
            logger:Logger = logging.getLogger(__name__)
    ):
        self.target_dir = target_dir
        self.logger = logger
    
    def load_chapter_section_articles(self):
        target_path = os.path.join(self.target_dir, "chapters")
        os.makedirs(target_path, exist_ok=True)

        for i in tqdm(range(1,14), desc="Loading Chapters.."):
            chapter = Chapter(CHAPTER_URL + str(i) + "/")
            chapter.set_title()
            chapter.chapter_number = str(i)
            chapter.set_sections_and_articles()

            save_to_pkl(chapter, os.path.join(target_path, f"chapter_{str(i)}.pkl"))
        
        self.logger.info(f"Downloaded Chapters to {self.target_dir}")
        
    def load_recitals(self):
        target_path = os.path.join(self.target_dir, "recitals")
        os.makedirs(target_path, exist_ok=True)

        for i in tqdm(range(1,181), desc="Loading Recitals.."):
            recital = Recital(RECITAL_URL + str(i) + "/")
            recital.recital_number = str(i)

            recital.set_content()
            recital.set_chunks()

            save_to_pkl(recital, os.path.join(target_path, f"recital_{str(i)}.pkl"))

        self.logger.info(f"Downloaded Recitals to {self.target_dir}")

    def load_annexes(self):
        target_path = os.path.join(self.target_dir, "annexes")
        os.makedirs(target_path, exist_ok=True)

        for i in tqdm(range(1,14), desc="Loading Annexes.."):
            annex = Annex(ANNEX_URL + str(i) + "/")
            annex.annex_number = str(i)
            annex.set_title()
            annex.set_chunks()

            save_to_pkl(annex, os.path.join(target_path, f"annex_{str(i)}.pkl"))

def main(args: argparse.Namespace):
    logging.basicConfig(level=logging.INFO)

    loader = DataLoader(target_dir=args.target_dir)
    loader.load_chapter_section_articles()
    loader.load_recitals()
    loader.load_annexes()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--target_dir', type=str, default="data/ai act")

    args = parser.parse_args()
    main(args)