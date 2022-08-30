import pymysql

# Test: Might have to execute this once
connect_MySQL = pymysql.connect(host='127.0.0.1', user='root', password='my-secret-pw')
connect_MySQL.cursor().execute('CREATE DATABASE Plom;')
connect_MySQL.close()