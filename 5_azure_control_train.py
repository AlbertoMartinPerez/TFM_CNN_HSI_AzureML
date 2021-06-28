import azureml.core
from azureml.core import Workspace, Dataset, Environment, Experiment, ScriptRunConfig
from azureml.core.conda_dependencies import CondaDependencies
import os, shutil

# Flag to indicate if we wan to use an already defined 
# environment (True) or create a new one (False)
use_registered_environment = True

# Available personal Workspace Compute Clusters (you may have different ones):
# CPU cluster = 'CPU-CompCluster'
# GPU cluster = 'GPU-CompCluster'
cluster_name = 'GPU-CompCluster'


#*###########################
#* CONNECT TO THE WORKSPACE
#*
# Load the workspace from the saved config file
ws = Workspace.from_config()
print('Ready to use Azure ML {} to work with {}'.format(azureml.core.VERSION, ws.name))


#*###########################
#* GET DEFAULT DATASTORE AND 
#* EXTRACT DATASETS PATHS
#*
# Get the default datastore
default_ds = ws.get_default_datastore()

# A dataset is used to reference the data you uploaded to Azure Blob Storage.
# Datasets are an abstraction layer on top of your data that are designed to improve reliability and trustworthiness.
# From the default datastore, we want to extract the uploaded file (.mat) available in the Azure Blob Storage
# The path of the file should be the one available in the Azure Blob Container directory and not the one created locally on Azure Machine Learning > Author > Notebooks
# Dataset.File.from_files() returns a 'FileDataset' object.

# Create a file dataset from the path on the datastore (this may take a short while) for the Ground Truth Maps
gt_ds = Dataset.File.from_files(path=(default_ds, 'NEMESIS_images/GroundTruthMaps/*.mat'))
        
# Create a file dataset from the path on the datastore (this may take a short while) for the preProcessedImages
preProcessed_ds = Dataset.File.from_files(path=(default_ds, 'NEMESIS_images/preProcessedImages/*.mat'))


#*###########################
#* CREATE A TRAINING SCRIPT
#*
# Create a folder for the experiment files
experiment_folder = 'PyTorch_training_from_file_datasets'
os.makedirs(experiment_folder, exist_ok=True)
print(experiment_folder, 'folder created')

# Copy the necessary Python files into the experiment folder
shutil.copy('./example_CubeManager.py', os.path.join(experiment_folder, "example_CubeManager.py"))
shutil.copy('./hsi_dataManager.py', os.path.join(experiment_folder, "hsi_dataManager.py"))
shutil.copy('./metrics.py', os.path.join(experiment_folder, "metrics.py"))
shutil.copy('./nn_models.py', os.path.join(experiment_folder, "nn_models.py"))


#*###############################
#* DEFINE AN ENVIRONMENT OR 
#* USED A REGISTERED ENVIRONMENT
#*

env_name = "PyTorch_Conv2DNet-experiment-env"

if use_registered_environment:
    # get the registered environment
    pytorch_env = Environment.get(workspace=ws, name=env_name)

    print('Using the already defined environment', pytorch_env.name, '.')

else:
    # Create a Python environment for the experiment
    pytorch_env = Environment(env_name)
    pytorch_env.python.user_managed_dependencies = False # Let Azure ML manage dependencies

    # Create a set of package dependencies (conda or pip as required)
    pytorch_packages = CondaDependencies.create(conda_packages=['scikit-learn','ipykernel','matplotlib','numpy', 'pillow', 'pip'],
                                                pip_packages=['azureml-sdk','pyarrow', 'torch', 'scipy', 'tqdm'])

    # Add the dependencies to the environment
    pytorch_env.python.conda_dependencies = pytorch_packages

    print(pytorch_env.name, 'defined.')

    # Register the environment
    pytorch_env.register(workspace=ws)


#*############################
#* USE ENVIRONMENT TO RUN
#* A SCRIPT AS AN EXPERIMENT IN
#* A COMPUTE CLUSTER
#*

# Create a script config (Uses docker to host environment)
# Using 'as_download' causes the files in the file dataset to be downloaded to 
# a temporary location on the compute where the script is being run.
# Reference to datasets and the paths where they will be downloaded in the environment
script_config = ScriptRunConfig(source_directory=experiment_folder,
                                script='example_CubeManager.py',
                                arguments = ['--input-gt-data', gt_ds.as_named_input('gtMaps_data').as_download(),
                                '--input-preProcessed-data', preProcessed_ds.as_named_input('preProcessed_data').as_download(),
                                ],
                                environment=pytorch_env,
                                compute_target=cluster_name
                                )

#*################################
#* SUBMIT THE EXPERIMENT TO AZURE
#*
# submit the experiment
experiment_name = 'exp-3-PyTorch-train'
experiment = Experiment(workspace=ws, name=experiment_name)
run = experiment.submit(config=script_config)