from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime
from groups.group_downloads import download_tasks
from groups.group_transforms import transform_tasks
 
with DAG('group_dag', start_date=datetime(2022, 1, 1), 
    schedule_interval='@daily', catchup=False, tags=['quincytromp']) as dag:

    downloads = download_tasks()

    check_files = BashOperator(
        task_id='check_files',
        bash_command='sleep 10'
    )
    
    transforms = transform_tasks()
 
    downloads >> check_files >> transforms