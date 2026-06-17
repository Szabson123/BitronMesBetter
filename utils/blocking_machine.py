def get_assembly_form(cur, phase_id, internal_code,):
    query = '''
                SELECT a.[AssemblyFormID]
                    ,a.[Description]
                    ,a.[SupplyNumber]
                    ,a.[InternalCode]
                    ,a.[MachineSetupId]
                    ,a.[Active]
                    ,a.[PeopleId]
                    ,a.[CreationDate]
                    ,a.[KPI_Enable]
                FROM [Eclipse].[dbo].[AssemblyForms] a
                JOIN [Eclipse].[dbo].ProcessesMatrix m
                    ON a.[AssemblyFormID] = m.[AssemblyFormID]
                WHERE m.PhaseId = ?
                    AND a.InternalCode = ?
            '''
    cur.execute(query, (phase_id, internal_code, ))

    return cur.fetchone()


def get_counted_fails(cur, counter, phase_id, internal_code,):
    query = '''
                WITH OstatniePomiary AS (
                    SELECT TOP (?) 
                        h.IDMeasure
                    FROM [Measure].[dbo].[HeaderDataLog] h
                    WHERE h.IdPhase = ?
                    AND h.IdParts = ?
                    AND h.TestDateTime >= DATEADD(hour, -48, GETDATE())
                    ORDER BY h.TestDateTime DESC
                )

                SELECT m.Item AS Nazwa_bledu
                    ,COUNT(*) AS Ilosc
                FROM OstatniePomiary op
                JOIN [Measure].[dbo].[MeasureDataLog] m
                    ON m.IDMeasure = op.IDMeasure
                WHERE m.Item != 'Result'
                GROUP BY m.Item
                ORDER BY Ilosc DESC;
            '''
    cur.execute(query, (counter, phase_id, internal_code, ))

    return cur.fetchone()


def get_counter(cur, phase_id):
    query = '''
        SELECT counter FROM public.mes_checkmachine
        WHERE phase_id = %s
    '''

    cur.execute(query, (phase_id, ))
    data = cur.fetchone()
    
    if data is None:
        return 0
        
    return data["counter"]


def increment_or_create_counter(cur, phase_id: int) -> int:
    query = '''
        INSERT INTO public.mes_checkmachine (phase_id, counter)
        VALUES (%s, 1)
        ON CONFLICT (phase_id) 
        DO UPDATE SET counter = public.mes_checkmachine.counter + 1
        RETURNING counter;
    '''
    cur.execute(query, (phase_id,))
    result = cur.fetchone()
    
    if isinstance(result, dict):
        return result["counter"]
    return result[0]


def pass_password(cur, phase_id: int, internal_code: int, password_attempt: str) -> bool:
    pwd_query = '''
        SELECT who FROM public.mes_passwordtounlock 
        WHERE passw = %s;
    '''
    cur.execute(pwd_query, (password_attempt,))
    user_row = cur.fetchone()
    
    if not user_row:
        return False
        
    who_unlocked = user_row["who"] if isinstance(user_row, dict) else user_row[0]
    
    update_query = '''
        INSERT INTO public.mes_checkmachine (phase_id, counter)
        VALUES (%s, 1)
        ON CONFLICT (phase_id) 
        DO UPDATE SET counter = 1;
    '''
    cur.execute(update_query, (phase_id,))
    
    log_query = '''
        INSERT INTO public.mes_unlockhistory (phase_id, internal_code, who, date_time)
        VALUES (%s, %s, %s, NOW());
    '''
    cur.execute(log_query, (phase_id, internal_code, who_unlocked))
    
    return True
