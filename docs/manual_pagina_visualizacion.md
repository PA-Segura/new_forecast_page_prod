# Manual de Usuario - Visualizador de Pronóstico de Calidad del Aire

## 1. Introducción

Esta página permite la visualización del **Pronóstico de Calidad del Aire Basado en Redes Neuronales**. Permite consultar pronósticos de concentraciones de los contaminantes atmosféricos generados a partir de un modelo de aprendizaje automático basado en la arquitectura Visual Transformers que integra observaciones de las estaciones de las redes de monitoreo de la Megalópolis y pronósticos meteorológicos del modelo WRF-ARW.

El pronóstico es un desarrollo del **Instituto de Ciencias de la Atmósfera y Cambio Climático (ICAyCC)** de la **Universidad Nacional Autónoma de México (UNAM)** para la **Comisión Ambiental de la Megalópolis (CAMe)**.

---

## 2. Navegación General

La página de visualización cuenta con una barra de navegación superior que permite acceder a las cuatro secciones principales:

| Sección | Descripción |
|---|---|
| **Página Principal** | Mapa interactivo, serie de tiempo de ozono, indicadores de probabilidad |
| **Otros Contaminantes** | Series de tiempo de PM10 y PM2.5 |
| **Históricos** | Consulta de pronósticos de fechas anteriores |
| **Acerca del Pronóstico** | Metodología, créditos e información del sistema |

---

## 3. Página Principal

La página principal presenta el pronóstico actual de calidad del aire por ozono, series de tiempo y probabilidades de excedencia de umbrales para ozono. 

### 3.1 Mapa Interactivo de Estaciones

![Mapa de pronóstico de calidad del aire](assets/mapa_forecast.png)

El mapa muestra las estaciones de monitoreo de la ZMVM como puntos coloreados según la **concentración máxima de ozono pronosticada para las próximas 24 horas**. Los colores corresponden a la clasificación de calidad del aire:

| Categoría | Color | Rango de O₃ (ppb) |
|---|---|---|
| Buena | Verde | 0 – 57 |
| Aceptable | Amarillo | 58 – 89 |
| Mala | Naranja | 90 – 134 |
| Muy Mala | Rojo | 135 – 174 |
| Extremadamente Mala | Morado | 175 o más |

**Interacción con el mapa:**
- **Posicion del cursor:** al posicionar el puntero sobre una estación se despliega un cuadro con el valor de concentración máxima esperada, la clave y el nombre de la estación.
- **Zoom:** se puede hacer zoom con la rueda del ratón o los botones de la barra de herramientas.

Las capas del mapa incluyen los límites de la Ciudad de México, el Estado de México y Morelos.

### 3.2 Resumen del Máximo Pronóstico

A continuación del mapa, se muestra un cuadro con el resumen del pronóstico máximo de ozono, con el formato:

> **Máxima concentración pronosticada: XX.X ppb en [Nombre de Estación], a las HH:MM hrs.**
> *(Pronóstico del DD de Mes de AAAA a las HH:MM hrs.)*

Este resumen indica cuál es la estación donde se espera la mayor concentración de ozono y a qué hora se pronostica que suceda.

### 3.3 Selector de Estación

![Menú desplegable para selección de estación](assets/sel_est_dropmenu.png)

En la sección de la serie de tiempo de ozono se encuentra un **menú desplegable** que permite seleccionar la estación de monitoreo de interés. Al cambiar la estación seleccionada:
- Se actualiza la serie de tiempo de ozono.
- Se actualizan los indicadores de probabilidad.
- Se resalta la estación seleccionada en los gráficos.

### 3.4 Serie de Tiempo de Ozono

![Serie de tiempo de concentraciones de ozono](assets/serie_tiempo_ozono.png)

El gráfico de serie de tiempo muestra las concentraciones horarias de ozono en partes por billón (ppb). En el título se indica la fecha y hora del último pronóstico disponible.

**Elementos del gráfico:**

| Elemento | Color | Descripción |
|---|---|---|
| Observaciones de la estación seleccionada | Azul marino | Últimas 48 horas de observaciones registradas |
| Pronóstico de la estación seleccionada | Rojo | Pronóstico para las próximas 24 horas |
| Observaciones de otras estaciones | Gris claro | Contexto de las otras estaciones de monitoreo |
| Pronósticos de otras estaciones | Azul claro | Pronósticos de las demás estaciones |

La serie de tiempo permite identificar tendencias, comparar el comportamiento de la estación seleccionada con el resto de la red.

### 3.5 Indicadores de Probabilidad

Debajo de la serie de tiempo se muestran **indicadores** que representan la probabilidad de superar diferentes umbrales de concentración de ozono para la estación seleccionada:

| Indicador | Umbral |
|---|---|
| Media de más de 50 ppb en 8 hrs | Promedio móvil de 8 horas superior a 50 ppb |
| Umbral de 90 ppb | Concentración horaria superior a 90 ppb |
| Umbral de 120 ppb | Concentración horaria superior a 120 ppb |
| Umbral de 150 ppb | Concentración horaria superior a 150 ppb |

Cada indicador muestra una probabilidad de 0 a 1 con código de colores:
- **Verde:** probabilidad baja (< 0.2)
- **Amarillo:** probabilidad media (0.2 – 0.5)
- **Rojo:** probabilidad alta (> 0.5)

---

## 4. Otros Contaminantes

Esta página presenta las series de tiempo de **material particulado (PM10 y PM2.5)** para la estación seleccionada.

### 4.1 Selector de Estación

En esta sección se cuenta con un menú desplegable para seleccionar la estación de monitoreo. Al cambiar la estación, se actualizan ambas gráficas de PM10 y PM2.5.

### 4.2 Series de Tiempo de PM10 y PM2.5

![Series de tiempo de concentraciones de PM10 y PM2.5](assets/series_tiempo_pms.png)

Se presentan dos gráficos separados:

**PM10 (µg/m³):**
- Observaciones de la estación seleccionada (resaltada).
- Pronóstico regional para las próximas 24 horas con tres curvas: valor mínimo, promedio y máximo pronosticado para toda la región.

**PM2.5 (µg/m³):**
- Observaciones de la estación seleccionada (resaltada).
- Pronóstico regional para las próximas 24 horas con tres curvas: valor mínimo, promedio y máximo pronosticado para toda la región.

A diferencia del ozono los pronósticos de PM10 y PM2.5 son regionales; se muestra el rango esperado (mínimo, promedio, máximo) para el conjunto de las diferentes estaciones de monitoreo, y las observaciones específicas de cada estación.

---

## 5. Históricos

La página de Históricos permite consultar pronósticos generados en fechas anteriores. 

### 5.1 Selectores

La página de pronósticos históricos cuenta con cuatro controles para configurar la consulta:

| Selector | Descripción |
|---|---|
| **Estación** | Menú desplegable con las estaciones de las redes de monitoreo |
| **Hora** | Menú desplegable de 00:00 a 23:00 hrs, con botones de flecha (← →) para navegar hora por hora |
| **Contaminante** | Menú desplegable: O₃, PM2.5 o PM10 |
| **Fecha** | Selector de fecha en formato DD/MM/AAAA, con botones de flecha (← →) para navegar día por día |

Los botones de flecha (← →) junto al selector de hora y fecha permiten avanzar o retroceder sin necesidad de despegar los menús de selección.

### 5.2 Gráfico de Pronóstico Histórico

Al seleccionar los parámetros, se muestra la serie de tiempo correspondiente al pronóstico generado en la fecha y hora indicadas. El título del gráfico se actualiza automáticamente para actualizar nombre de contaminante, fecha, hora y estación seleccionada:

> *Concentraciones de Ozono (ppb) – Pronóstico del 15 de Enero de 2026 a las 09:00 hrs. – Villa de las Flores*

---

## 6. Acerca del Pronóstico

Esta página contiene información descriptiva del sistema, así como créditos y contacto. 

---

## 7. Referencia Técnica

### 7.1 Clasificación de Calidad del Aire

Los umbrales de calidad del aire utilizados en el sistema:

**Ozono (O₃) en ppb:**

| Categoría | Rango | Color |
|---|---|---|
| Buena | 0 – 57 | Verde |
| Aceptable | 58 – 89 | Amarillo |
| Mala | 90 – 134 | Naranja |
| Muy Mala | 135 – 174 | Rojo |
| Extremadamente Mala | ≥ 175 | Morado |

### 7.2 Tipos de Datos en las Series de Tiempo

| Tipo | Fuente | Ventana temporal |
|---|---|---|
| Observaciones | Redes de monitoreo (datos horarios reales) | Últimas 48 horas |
| Pronóstico de O₃ | Modelo neuronal, por estación individual | Próximas 24 horas |
| Pronóstico de PM10/PM2.5 | Modelo neuronal, valores regionales (min, promedio, max) | Próximas 24 horas |

### 7.3 Diferencia entre Pronósticos por Estación y Regionales

- **Ozono (O₃):** el modelo genera un pronóstico **individual por cada estación** de monitoreo. Esto permite comparar pronóstico con las observaciones de esa estación.
- **PM10 y PM2.5:** el modelo genera un pronóstico **regional** que corresponde a los valores mínimos, promedio y máximos. Las observaciones mostradas sí son específicas de la estación que sea seleccionada.

### 7.4 Indicadores de Probabilidad

Los indicadores de probabilidad muestran la estimación del modelo sobre la probabilidad de que se excedan ciertos umbrales de concentración de ozono en las próximas 24 horas para la estación seleccionada:

| Indicador | Significado |
|---|---|
| Media > 50 ppb en 8 hrs | Probabilidad de que el promedio móvil de 8 horas supere 50 ppb |
| Umbral de 90 ppb | Probabilidad de que la concentración horaria supere 90 ppb (inicio de categoría "Mala") |
| Umbral de 120 ppb | Probabilidad de que la concentración horaria supere 120 ppb |
| Umbral de 150 ppb | Probabilidad de que la concentración horaria supere 150 ppb (próximo a "Muy Mala") |

#### 7.4.1 Formulación Matemática

Las probabilidades se calculan modelando el error del pronóstico como una variable aleatoria con distribución normal. Sea {y}_t el valor pronosticado para la hora t, y sea  e = y - \hat{y} el error de pronóstico, donde y es el valor real observado. Se asume que el error sigue una distribución normal:
![Distribución del error e = y - ŷ](assets/e_y_ydot__e_N_mu_sigma.png)


donde \mu  y \sigma son la media y desviación estándar del error, estimados a partir de datos históricos de validación del modelo.

**Probabilidad de superar un umbral puntual (casos 90, 120 y 150 ppb):**

Para los umbrales puntuales, se utiliza el máximo valor pronosticado en las próximas 24 horas por estación dada:

\[
\hat{y}_{\max} = \max_{t=1}^{24} \hat{y}_t
\]

La probabilidad de que el valor real supere un umbral \( T \) se calcula como:

\[
P(y > T) = P(\hat{y}_{\max} + e > T) = P\left(e > T - \hat{y}_{\max}\right) = 1 - \Phi\left(\frac{T - \hat{y}_{\max} - \mu}{\sigma}\right)
\]

donde \( \Phi \) es la función de distribución acumulada (CDF) de la distribución normal estándar.

Los parámetros utilizados para el error del máximo en 24 horas son:
- \( \mu = 5.08 \) ppb
- \( \sigma = 18.03 \) ppb

**Probabilidad de superar la media móvil de 8 horas > 50 ppb (caso 1):**

Se calcula el promedio móvil centrado de 8 horas sobre el vector de pronóstico:

\[
\bar{y}_t^{(8)} = \frac{1}{8} \sum_{i=t-3}^{t+4} \hat{y}_i
\]

Para cada ventana de 8 horas, se calcula la probabilidad de que el promedio real supere el umbral \( T = 50 \) ppb:

\[
P\left(\bar{y}_t^{(8)} + e > T\right) = 1 - \Phi\left(\frac{T - \bar{y}_t^{(8)} - \mu}{\sigma}\right)
\]

Los parámetros del error para la media móvil de 8 horas son:
- \( \mu = -0.43 \) ppb
- \( \sigma = 6.11 \) ppb

El indicador final reporta la probabilidad máxima entre todas las ventanas de 8 horas en las 24 horas pronosticadas:

\[
P_{\text{indicador}} = \max_{t} \; P\left(\bar{y}_t^{(8)} + e > 50\right)
\]


---

## 8. Ejemplos para taller de capacitación

Propuesta de casos de ejemplos para taller de formación de usuarios. 

### 8.1 Ej 1: Pronóstico de las 7:00 hrs

**Escenario:** Por la mañana se consulta el visualizador con pronóstico de las 7:00 hrs. Se muestra el último pronóstico disponible.

1. **Revisar resumen del máximo pronóstico** (cuadro debajo del mapa).
   Lectura: *"Máxima concentración pronosticada: 142 ppb en Pedregal (PED), a las 14:00 hrs."*
   - Interpretación: Pronóstico indica que el pico de ozono ocurrirá hacia las 14:00 hrs y que la estación con concentración más alta sería Pedregal, con 142 ppb.

2. **Revisar el mapa.**
   - Identificar estaciones que aparecen en naranja (Mala), rojo (Muy Mala) o morado (Extremadamente Mala).
   - i.e.: "Estaciones del suroeste y centro (Pedregal, y CCA) muestran valores altos; el mapa indica condiciones desfavorables en esa parte de la ciudad."

3. **Revisar indicadores de probabilidad.**
   - En el indicador **"Umbral de 120 ppb"**: si el valor está en **amarillo** (p. ej. 0.45), la probabilidad de superar 120 ppb es moderada.
   - En el indicador **"Umbral de 150 ppb"**: si está en **rojo** (p. ej. 0.72), la probabilidad de superar 150 ppb es **alta**.
   - Mensaje taller: "Cuando uno o ambos indicadores (120 ppb y 150 ppb) están en amarillo o rojo, se recomienda estar atentos a los avisos de calidad del aire y, si aplica, a las medidas de contingencia."

4. **Opcional: cambiar la estación en el menú desplegable** y comparar la serie de tiempo de ozono y los indicadores de otra estación (por ejemplo, una de la zona norte) para ver que el riesgo no es homogéneo en toda la Megalópolis.

5. **Ver los diferentes valores pronosticados** El pronóstico basado en aprendizaje automático es mejor en valores promedio, es interesante ver los pronósticos de las diferentes estaciones para ver si en promedio se esperan valores elevados de concentraciones. 

**Resumen :** En este ejemplo se observa: (a) valor máximo pronosticado y hora del pico, (b) varias estaciones con valores altos en el mapa, (c) interpretación de indicadores de probabilidad (120 y 150 ppb) cuando son altos o muy altos.

---

### 8.2 Ejemplo 2: Interpretación con probabilidad muy alta (episodio severo)

**Escenario:** Consulta a las 7:00 hrs; el pronóstico, día indica un episodio de ozono más severo.

- **Resumen:** "Máxima concentración pronosticada: 168 ppb en Instituto de Ciencias de la Atmósfera y Cambio Climático (CCA), a las 15:00 hrs."
  - 168 ppb corresponde a la categoría **Muy Mala** (≥ 135 ppb).

- **Indicadores:**  
  - "Umbral de 120 ppb: en **rojo**, probabilidad por ejemplo 0.85 (muy alta)."  
  - "Umbral de 150 ppb: también en **rojo**, probabilidad por ejemplo 0.62 (alta)."  
  - Conclusión: "El modelo está pronosticado día con alto riesgo de superar de umbrales; se sugiere seguir de cerca concentraciones de ozono."

---

### 8.3 Ejemplo 3: Verificación de un episodio pasado con la página Históricos (14 de febrero de 2026)

**Objetivo:** Comprobar qué pronosticó el modelo para un día concreto (episodio del 14 de febrero de 2026) y contrastarlo con observaciones de ese día.

1. Ir a **Históricos** desde el menú superior.

2. Configurar los filtros:
   - **Estación:** por ejemplo Pedregal (PED) o la que se haya usado en el episodio.
   - **Hora del pronóstico:** elegir la hora en que típicamente se consulta (p. ej. **07:00 hrs**), que corresponde al pronóstico disponible esa mañana.
   - **Contaminante:** Ozono (O₃).
   - **Fecha:** **14/02/2026**.

3. Interpretar el gráfico que aparece:
   - "Este es el pronóstico que un usuario habría visto la mañana del 14 de febrero de 2026 para las siguientes 24 horas en esa estación."
   - Observar la curva de pronóstico (en rojo): valor máximo pronosticado en la serie y hora aproximada del pico.
   - Ejemplo: "El modelo pronosticó un máximo de alrededor de 138 ppb hacia las 15:00 hrs en Pedregal para ese día."

4. **Verificación:**
   - "Podemos comparar: el pronóstico de la mañana si indicaba un día con riesgo alto." 
   - "La página Históricos sirve para revisar qué mostró el sistema en episodios pasados y evaluar el pronóstico a posteriori."

---

*Última actualización del manual: Febrero 2026*
