"""Tablero financiero (pilot): datos curados + KPIs servidos por endpoint.

En el pilot la fuente es una semilla con los números YA CURADOS por el equipo de
finanzas (extraídos del cierre CONTPAQi). La arquitectura es 'data por endpoint':
en Paso 1 se cambia la semilla por el conector a la BD/origen sin tocar el tablero.
"""
