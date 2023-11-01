
from sqlalchemy import create_engine
import pandas as pd
import dotenv
import os

def get_connection_info(db):
    """Gets the connection information for the specified database.

    Args:
        db: The name of the database to connect to.

    Returns:
        A tuple containing the database name, username, and password.
    """
    dotenv.load_dotenv((os.getcwd())+"/setup/.env")
    if db.lower() == 'postgres':
        database = os.environ.get("POSTGRES_DB")
        user = os.environ.get("POSTGRES_USER")
        password =os.environ.get("POSTGRES_PASSWORD")
    elif db.lower() == 'mysql':
        database = os.environ.get("MYSQL_DATABASE")
        user = os.environ.get("MYSQL_user")
        password =os.environ.get("MYSQL_ROOT_PASSWORD")
    
    return database, user, password

def get_data_from_db(connection_string,query):
    """Gets data from a database using a SQL query.

    Args:
    connection_string: The connection string to the database.
    query: The SQL query to execute.

    Returns:
    A Pandas DataFrame containing the results of the query, or a string error message if the query fails.
    """
    try:
        postgres_engine = create_engine(connection_string)
        connection = postgres_engine.connect()
        result_df = pd.read_sql(query,connection)
        connection.close()
        return result_df
    except Exception as e:
        return str(e)

def get_aggregated_result(ms_df,pg_df,join_column,group_by_column):
    """
    This function will left join 2 dataframes on join_column.

    Args:
    ms_df: MySQL DF.
    pg_df: Postgres DF.
    join_column: Column on which we need to join
    group_by_column: Column on which we need to group by.

    Returns:
    A Pandas DataFrame which has calculated it's values.
    """
    joined_df = pd.merge(ms_df,pg_df,how='left',on=join_column)
    return joined_df.groupby(group_by_column)['lesson_id'].count() 


def write_to_csv_on_s3(df_to_write,path):
    """
    This function will write dataframe to s3 bucket.
    As of now, we don't have s3 credentials so that part is not part of code

    Args:
    df_to_write: Pandas dataframe that will be written on s3.
    path: Path where to write dataframe
    """

    # Code to connect to s3
    try:
        df_to_write.to_csv(path)
    except Exception as e:
        print(f"Write operation failed by error {e}")


def main():
    # PostGres connection details
    pg_database, pg_user, pg_password = get_connection_info('postgres')
    pg_connection_string = f"postgresql+psycopg2://{pg_user}:{pg_password}@localhost/{pg_database}"
    pg_query = """select * from mindtickle_users where active_status = 'active';"""
    
    # Get data from PostGres
    pg_df = get_data_from_db(connection_string=pg_connection_string,query=pg_query)

    # Stop execution if get_data_from_db fails. 
    if isinstance(pg_df, str):
        return "Dataframe from PostGres is empty"
    
    # Get users tuple which can be used in mySQL to filter data.
    unique_users = tuple(pg_df.user_id.tolist())

    # MySQL connection details
    ms_database, ms_user, ms_password = get_connection_info('mysql')
    ms_connection_string = f"mysql+mysqlconnector://{ms_user}:{ms_password}@localhost/{ms_database}"
    ms_query = f'select * from lesson_completion where DATE(completion_date) > CURDATE() - INTERVAL 30 DAY and user_id in {unique_users};'
    
    # Get data from MySQL
    ms_df = get_data_from_db(connection_string=ms_connection_string,query=ms_query)

    # Stop execution if get_data_from_db fails. 
    if isinstance(ms_df, str):
        return "Dataframe from MySQL is empty"

    # Get transformed dataframe
    agg_df = get_aggregated_result(ms_df,pg_df,'user_id','user_name')
    
    # Write to file location, if agg_df has some data.
    if len(agg_df) == 0:
        print("File is empty.")
    else:
        path = os.getcwd() + "\\output.csv"
        write_to_csv_on_s3(agg_df,path)

if __name__ == "__main__":
    main()



