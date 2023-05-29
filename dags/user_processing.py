from airflow import DAG
from datetime import datetime
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import json
from pandas import json_normalize

def _process_user(ti):
    user=ti.xcom_pull(task_ids='extract_user')
    user = user['results'][0]
    processed_user = json_normalize({
        'firstname': user['name']['first'],
        'lastname': user['name']['last'],
        'country': user['location']['country'],
        'username': user['login']['username'],
        'password': user['login']['password'],
        'email': user['email']})
    processed_user.to_csv('/tmp/processed_user.csv', index=None, header=False)

def _store_user():
    hook = PostgresHook(postgres_conn_id='postgres')
    hook.copy_expert(
        sql="COPY users FROM stdin WITH DELIMITER as ','",
        filename='/tmp/processed_user.csv'
    )


with DAG(dag_id='user_processing', start_date=datetime(2023, 5, 26), 
         schedule_interval='@daily', catchup=False, tags=['quincytromp']) as dag:
    
    create_table = PostgresOperator(
        task_id='create_table',
        postgres_conn_id='postgres',
        sql='''
            CREATE TABLE IF NOT EXISTS users (
                firstname TEXT NOT NULL,
                lastname TEXT NOT NULL,
                country TEXT NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                email TEXT NOT NULL
            );
        '''
    )

## Testing create_table
# In your terminal, type: docker exec -it airflow-docker-airflow-scheduler-1 /bin/bash
# and hit Enter. You are now in the docker container, in the VM where the scheduler of airflow 
# works. From there you can access the airflow CLI. If you type: airflow -h you will 
# see all the commands that you can execute with the airflow CLI. To test task create_table, 
# type: airflow tasks test user_processing create_table 2023-05-26 and hit Enter. You can
# see in the terminal that the task was marked SUCCESS.

    is_api_available = HttpSensor(
        task_id='is_api_available',
        http_conn_id='user_api', 
        endpoint='api/'
    )

    extract_user = SimpleHttpOperator(
        task_id='extract_user',
        http_conn_id='user_api',
        endpoint='api/',
        method='GET',
        response_filter= lambda response: json.loads(response.text),
        log_response=True
    )

    process_user = PythonOperator(
        task_id='process_user',
        python_callable=_process_user
    )

    store_user = PythonOperator(
        task_id='store_user',
        python_callable=_store_user
    )

    create_table >> is_api_available >> extract_user >> process_user >> store_user

## Checking if processed_user.csv was created
# In your terminal, type: docker-compose ps and hi Enter. Then copy the name of the worker and type: 
# docker exec -it airflow-docker-airflow-worker-1 /bin/bash
# Once you are in the container, type: ls /tmp/ and hit Enter. You should see now the 
# file processd_user.csv