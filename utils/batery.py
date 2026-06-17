from database import CONNECTION_STRING
from pyodbc import connect
from datetime import datetime

def get_batery_passivation(cursor, sn):
    query = '''SELECT TOP (1) [TestDateTime] FROM [Measure].[dbo].[HeaderDataLog] WHERE MSN = ? AND Result=1 ORDER BY TestDateTime DESC'''
    cursor.execute(query, (sn, ))

    return cursor.fetchall()


def main_util_batery_check(sn: str):
    date_strp = sn[:8]

    try:
        validate_date = datetime.strptime(date_strp, "%d%m%Y")
    except ValueError:
        return {"error": "Error podany sn nie posiada odpowiedniej daty (DDMMYYYY) proszę sprawdź czy to bateria ItalGas"}
    
    today = datetime.now()
    age_difference = today - validate_date
    max_days = 167
    max_days_no_passivation = 330

    if age_difference.days < 0:
        return {"error": "Data z numeru seryjnego jest z przyszłości!"}
    
    # if age_difference.days > max_days_no_passivation:
    #     return {"error": "Bateria jest starsza niż rok"}
    
    if age_difference.days < max_days:
        return {"success": f"Bateria jest OK. Ma {age_difference.days} dni (mniej niż 5.5 miesiąca)."}
    else:
        with connect(CONNECTION_STRING) as conn:
            cursor = conn.cursor()
            database_check = get_batery_passivation(cursor, sn)

            if database_check:
                passivation_date = database_check[0][0]

                passivation_age = today - passivation_date

                if passivation_age.days < max_days:
                    return {"success": f"Bateria starsza kalendarzowo, ale przeszła pasywację {passivation_age.days} dni temu. OK."}
                else:
                    return {"error": f"Błąd: Pasywacja jest zbyt stara! Wykonano ją {passivation_age.days} dni temu (wymagane < 167)."}
            
            else:
                return {"error": "Bateria ma ponad 5.5 miesiąca i NIE przeszła testu pasywacji w systemie!"}