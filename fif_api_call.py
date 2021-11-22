###################################################################################################
# 
# Пример работы с API ФГИС "АРШИН" на python 3
#
# Получает актуальный реестр утвержденных типов СИ в полном объеме и сохраняет в Excel-файл
#
# Реализовано по документу "Руководство пользователя "Внешний публичный интерфейс"" , версия от 18.02.2021
# https://fgis.gost.ru/fundmetrology/cm/docs    
#
# ФГУП "ВНИИМС", Центр 102, 2021
# 
###################################################################################################

import sys
import configparser
import time
import datetime
import requests
import pandas

###################################################################################################
# функции
###################################################################################################

# выполняет вызов API 
# возвращает:
#  - результат вызова (True или False)
#  - в случае успеха - json-структуру, полученную от сервиса
def api_call( delay , url , params = None ):
    # задержка между запросами
    time.sleep( delay )
    # вызов веб-сервиса с использованием HTTP GET
    response = requests.get( url , params = params )
    # анализ кода возврата
    if response.status_code == 200:
        return ( True , response.json() )
    else:
        return ( False , None )

###################################################################################################
# основная программа
###################################################################################################

# чтение параметров из конфиг-файла fif_api_call.ini
config = configparser.ConfigParser()
config.read( "fif_api_call.ini" , encoding = "utf-8" )

# установка параметров начального запроса для получения количества элементов
params = { 'start': 0 , 'rows': 0 , 'sort': 'number asc' }

# количество элементов в списке
elements_count = 0

# выводим время начала импорта
print( 'Start time: ', datetime.datetime.now() )

# несколько раз пытаемся получить данные о количестве элементов
# как мы знаем, в настоящий момент АРШИН работает не всегда
for i in range( 0 , config.getint( "mit" , "attempts" ) ):
    # попытка получить количество элементов реестра утвержденных типов СИ
    result , response = api_call( config.getfloat( "app" , "delay" ) ,  config[ "mit" ][ "url" ] , params )
    if result:
        elements_count = response['result']['count']
        break

# если по истечению заданного количества попыток мы так и не смогли получить количество элементов, 
# то заканчиваем выполнение программы
if i == 9 and elements_count == 0:
    print( 'Не удалось получить данные о количестве элементов в реестре утвержденных типов СИ' )
    sys.exit( 1 )

# общее количество записей
print( 'Rows count: ' , elements_count )

# для результата используем DataFrame
columns = [ 'id' , 'number' , 'title', 'notation', 'manufacturer', 'part', 'factory_num', 'valid_for', 'procedure', 'interval', 'period', 'status' ]
rs_result = pandas.DataFrame( columns = columns )

# в цикле получаем список из 100 элементов
params[ 'rows' ] = 100
# цикл по всем записям с шагом 100 элементов
for params[ 'start' ] in range( 0 , elements_count , params[ 'rows' ] ):
    # выводим состояние
    print( 'Proccessing page ' , params[ 'start' ] // params[ 'rows' ] + 1 , '/' , elements_count // params[ 'rows' ] + int( bool( elements_count % params[ 'rows' ] ) ), ': ' , end = '' , flush = True )
    # пытаемся получить очередную страницу данных
    # производим вызов, пока не получим корректный ответ от сервиса
    result = False
    while not result:
        result , response = api_call( config.getfloat( "app" , "delay" ) , config[ "mit" ][ "url" ] , params )
    # цикл по списку записей на странице
    for item in response[ 'result' ][ 'items' ]:
        # выводим прогресс выполнения
        print( '.' ,  end = '' , flush = True )

        # получаем полные данные по конкретному элементу реестра
        # формируем url
        item_url = config[ "mit" ][ "url" ] + "/" + item[ 'mit_id' ]
        # производим вызов, пока не получим корректный ответ от сервиса
        item_result = False
        while not item_result:
            item_result , item_response = api_call( config.getfloat( "app" , "delay" ) , item_url )

        # формируем новую строку с набором значений
        row = {}
        try:
            row[ 'id' ] = item[ 'mit_id' ]
            row[ 'number' ] = item_response['general'].get( 'number' )
            row[ 'title' ] = item_response['general'].get( 'title' )
            if item_response['general'].get( 'notation' ) != None:
                row[ 'notation' ] = ';'.join( item_response['general'].get( 'notation' ) )
            row[ 'manufacturer' ] = item[ 'manufactorer' ]
            row[ 'part' ] = item_response['mit'].get( 'part' )
            row[ 'factory_num' ] = item_response['mit'].get( 'factory_num' )
            row[ 'valid_for' ] = item_response['mit'].get( 'valid_for' )
            row[ 'procedure' ] = item_response['mit'].get( 'procedure' )
            row[ 'interval' ] = item_response['mit'].get( 'interval' )
            row[ 'period' ] = item_response['mit'].get( 'period' )
            row[ 'status' ] = item_response['status']
        except Exception:
            row[ 'id' ] = 'Data error'

        # добавляем новую строку в резалтсет
        rs_result = rs_result.append( row , ignore_index = True )
    print( '' )

# сохраняем результаты в Excel-файл
rs_result.to_excel( config[ "mit" ][ "output_filename" ] , columns = columns , index = False )

# выводим время окончания импорта
print( 'Finish time: ', datetime.datetime.now() )
