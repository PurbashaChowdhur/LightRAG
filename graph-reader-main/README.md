# graph-reader
An implementation of the GraphReader approach to GraphRAG

## Development

### Installation
```bash
# [OPTIONAL] Create conda environment
conda create -n myenv
conda activate myenv

# Install requirements
pip install -r requirements.txt 
```

### Download data

Using the following command is possible to download the dataset used in the project. 

```bash
python src/datamodule/download.py
```

<details>
<summary><span style="font-weight: bold;">Command Line Arguments for download.py</span></summary>

  #### --data_dir
  Directory to save the dataset
</details>

### Create Neo4j Graph

Using the following command is possible to create the Neo4j Graph. 

```bash
python src/datamodule/graph.py
```

<details>
<summary><span style="font-weight: bold;">Command Line Arguments for graph.py</span></summary>

  #### --data_dir
  Directory of the dataset

  ### --neo4j_uri
  URI of the Neo4j Database

  ### --neo4j_username
  Username of the Neo4j Database

  ### --neo4j_password
  Password of the Neo4j Database

  ### --openai_api_key
  OpenAI API key
</details>

### Run Baseline model (BM25)

Using the following command is possible to run the baseline model. 

```bash
python src/run_baseline.py
```

<details>
<summary><span style="font-weight: bold;">Command Line Arguments for run_baseline.py</span></summary>

  
</details>