# TaxoTagger Webapp

![taxotagger-webapp](images/TaxoTagger-webapp.gif)


## Installation

1. Clone this repository
```bash
git clone https://github.com/MycoAI/taxotagger-webapp.git
```

2. Install the required packages
```bash
# Go to the taxotagger-webapp directory
cd taxotagger-webapp

# Create a new conda environment `taxotagger-webapp`
conda create -n taxotagger-webapp python=3.10

# Go to the conda environment
conda activate taxotagger-webapp

# Install the required packages
pip install -r requirements.txt
```

## Running the webapp

1. Set the environment variables `MYCOAI_HOME`

Set the environment variable `MYCOAI_HOME` to the path of the `data` directory in this repository. This directory contains the example vector databases for demo purposes.

```bash
# On Linux or MacOS
export MYCOAI_HOME=/path/to/taxotagger-webapp/data

# Or on Windows
set MYCOAI_HOME=C:\path\to\taxotagger-webapp\data
```

2. Start the webapp
```bash
# Make sure you are in the taxotagger-webapp directory and the conda environment is activated
cd taxotagger-webapp
conda activate taxotagger-webapp

# Run the webapp
streamlit run app.py
```

Then you can open the webapp in your browser by visiting the URL http://localhost:8501.

> [!NOTE]
> For the first time running, the webapp will download the embedding model files. This may take a few minutes depending on the internet connection speed.

## For production deployment

The vector databases provided in the `data` directory are for demo purposes only. To use the webapp in production, you should prepare the vector databases using the production data. To build the vector database, you can follow the instructions in the [TaxoTagger Doc](https://mycoai.github.io/taxotagger/latest/quickstart/#build-a-vector-database).