import pymysql

# Test: Might have to execute this once
# Put this line of code somewhere after DB has been initialize
connect_MySQL = pymysql.connect(host='127.0.0.1', user='root', password='my-secret-pw')
connect_MySQL.cursor().execute('CREATE DATABASE Plom;')
connect_MySQL.close()