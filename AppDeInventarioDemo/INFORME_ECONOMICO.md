# Informe de costos de producción y retorno

**Producto:** Atlas · Control de inventario de Krateroi  
**Fecha de referencia:** 8 de octubre de 2026  
**Moneda:** pesos chilenos (CLP) nominales  
**Tipo de estimación:** modelo conceptual, orden de magnitud; no es una cotización ni una promesa de rentabilidad.

## Resumen ejecutivo

La demo implementada es una aplicación local con interfaz web, API Python y SQLite persistente; no requiere dependencias externas ni servicios cloud. La inversión modelada abajo no es el costo ya incurrido en esta demo: estima convertirla en un SaaS comercial multiempresa. Autenticación, autorización, auditoría, importación de catálogos, soporte, observabilidad, respaldos administrados y continuidad operacional requieren trabajo y gasto adicional.

El escenario base estima **CLP 23,33 millones** para construir una primera versión comercial acotada, y **CLP 2,4 millones mensuales fijos** para operarla con un equipo pequeño, antes de impuestos y adquisición de clientes. Con una suscripción de **CLP 39.900 por empresa/mes** y un costo variable de **CLP 5.500 por cliente/mes**, el punto de equilibrio operacional aproximado es **70 clientes activos**. A 100 clientes, el excedente operacional estimado es **CLP 1,04 millones al mes**; a 20 clientes, todavía existe una pérdida mensual aproximada de **CLP 1,71 millones**.

## Qué se está estimando

La versión productiva contemplada es un SaaS web para pequeñas empresas, con un espacio de trabajo por cliente, catálogo, stock multiusuario, entradas/ventas/ajustes, niveles mínimos, exportaciones, reportes, copias de seguridad y una consola administrativa. Se consideran interfaces web responsivas, API, base de datos administrada, despliegue y pruebas; **no** se incluyen POS integrado, aplicación móvil nativa, hardware, ERP de terceros, inteligencia artificial, certificaciones ni migraciones a medida.

La demo guarda datos en un archivo SQLite del mismo equipo que ejecuta el servidor. No ofrece autenticación, multiempresa, roles, cifrado, backups automáticos, auditoría de acceso ni recuperación operacional. Para producción se necesitarían persistencia administrada, aislamiento por organización, control de acceso, monitoreo, respaldos probados y continuidad del servicio antes de cargar datos reales.

## Inversión inicial de desarrollo

Tarifas de planificación en CLP por hora, como costos de servicios profesionales cargados (no sueldo líquido). Las cifras permiten hacer visible la base del presupuesto; pueden variar con alcance, seniority, modalidad contractual e impuestos.

| Fase / especialidad | Esfuerzo | Tarifa de referencia | Subtotal |
|---|---:|---:|---:|
| Descubrimiento, procesos y definición funcional | 70 h | $28.000/h | $1.960.000 |
| Diseño UX/UI y prototipo | 80 h | $25.000/h | $2.000.000 |
| Frontend web y accesibilidad | 220 h | $28.000/h | $6.160.000 |
| API, modelo de datos y permisos | 230 h | $30.000/h | $6.900.000 |
| QA, seguridad básica y pruebas de aceptación | 90 h | $25.000/h | $2.250.000 |
| DevOps, despliegue, monitoreo y respaldos | 50 h | $30.000/h | $1.500.000 |
| Gestión de proyecto y documentación | 20 h | $22.000/h | $440.000 |
| Contingencia por alcance / integración (10%) | — | — | $2.121.000 |
| **Inversión inicial de referencia** | **760 h** |  | **$23.331.000** |

**Redondeo usado en el simulador:** CLP 23.330.000. La diferencia de CLP 1.000 respecto del desglose es el redondeo del modelo, no exactitud presupuestaria. Antes de contratar se debe reemplazar por una cotización y alcance acordado.

El total de horas antes de contingencia es 760 h. El cálculo de contingencia es 10% de los subtotales previos (CLP 21.210.000).

## Costo recurrente mensual a escala inicial

Presupuesto de operación con precio anualizado de servicios y dedicaciones compartidas. Las partidas de soporte y mantenimiento suponen capacidad parcial del equipo, no puestos exclusivos.

| Partida | Supuesto mensual | Costo mensual |
|---|---|---:|
| Aplicación, base de datos, respaldos y ambientes | Plan inicial; subir de tramo con uso | $420.000 |
| Monitoreo, correo transaccional, dominio y herramientas | Licencias y consumos básicos | $180.000 |
| Mantenimiento correctivo/evolutivo | 40 h × $30.000/h | $1.200.000 |
| Atención y operación de clientes | 20 h × $22.000/h | $440.000 |
| **Costos fijos mensuales del escenario base** |  | **$2.240.000** |

Para los cálculos financieros se redondea la base a **CLP 2.400.000/mes** y se agrega un supuesto de **CLP 5.500/cliente/mes** para almacenamiento, mensajería, soporte incremental y medios de pago. No se han supuesto descuentos tributarios, créditos cloud, trabajo gratuito ni costos financieros.

La capacidad requerida crecerá con el soporte real: a 200 clientes, 40 horas fijas de mantenimiento y 20 horas fijas de soporte podrían ser insuficientes. El escenario de escala es una primera aproximación y no un presupuesto cerrado de personal.

## Economía unitaria y punto de equilibrio

| Parámetro | Supuesto base |
|---|---:|
| Precio de suscripción por empresa / mes | $39.900 |
| Costo variable medio por empresa / mes | $5.500 |
| Contribución mensual por cliente | $34.400 |
| Costos fijos mensuales del modelo | $2.400.000 |
| Clientes de equilibrio operativo | 70 |
| Inversión de desarrollo usada para ROI | $23.330.000 |

Fórmulas:

- **Contribución unitaria** = precio mensual − costo variable mensual.
- **Punto de equilibrio** = techo(costos fijos / contribución unitaria) = techo($2.400.000 / $34.400) = **70 empresas**.
- **Resultado operativo mensual** = clientes × ($39.900 − $5.500) − $2.400.000.
- **Payback simple a 100 clientes** = $23.330.000 / ($3.440.000 − $2.400.000) = **22,4 meses**, manteniendo 100 clientes sin interrupción. No contempla la fase de captación previa.

El precio es una hipótesis para poder hacer sensibilidad, no un precio validado por clientes ni benchmark de mercado. El IVA no es ingreso ni costo en esta presentación; se excluye junto con impuesto a la renta.

## Escenarios mensuales estabilizados

| Escenario | Clientes activos | Ingreso recurrente | Costos variables | Costos fijos | Resultado operacional |
|---|---:|---:|---:|---:|---:|
| Piloto | 20 | $798.000 | $110.000 | $2.400.000 | **−$1.712.000** |
| Crecimiento | 75 | $2.992.500 | $412.500 | $2.400.000 | **$180.000** |
| Escala | 200 | $7.980.000 | $1.100.000 | $2.400.000 | **$4.480.000** |

Los márgenes anteriores son operacionales antes de depreciación, impuesto a la renta, costo comercial no incluido, cobranza incobrable y costos extraordinarios de incorporación.

## Escenario ilustrativo de tres años

Se supone rampa progresiva: 20 clientes promedio durante el año 1, 137,5 promedio durante el año 2 (de 75 a 200) y 200 promedio durante el año 3. Los clientes de cada año son promedios mensuales equivalentes; la tabla no modela cohortes, churn ni caja mes a mes.

| Año | Clientes promedio | Ingresos anuales | Costos variables | Costos fijos | Resultado operativo | Acumulado después de desarrollo* |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 20 | $9.576.000 | $1.320.000 | $28.800.000 | **−$20.544.000** | **−$43.874.000** |
| 2 | 137,5 | $65.835.000 | $9.075.000 | $28.800.000 | **$27.960.000** | **−$15.914.000** |
| 3 | 200 | $95.760.000 | $13.200.000 | $28.800.000 | **$53.760.000** | **$37.846.000** |

`*` El acumulado resta la inversión inicial de CLP 23,33 millones una sola vez al primer año. En este escenario, el payback sucede durante el tercer año; el retorno acumulado de tres años respecto de la inversión de desarrollo es aproximadamente **162%**: ($61.176.000 de resultado operativo acumulado − $23.330.000) / $23.330.000. No es flujo de caja descontado.

**Lectura del escenario:** el año 1 modela 20 clientes promedio durante los 12 meses y, por eso, tiene un resultado operativo de −CLP 20,544 millones. La adquisición real dentro del año y sus fechas de cobro deben reflejarse en un flujo de caja mensual.

## Sensibilidad del equilibrio

Manteniendo costos fijos de CLP 2,4 millones y costo variable de CLP 5.500 por cliente:

| Precio / mes | Contribución / cliente | Clientes de equilibrio |
|---:|---:|---:|
| $29.900 (−25%) | $24.400 | 99 |
| $39.900 (base) | $34.400 | 70 |
| $49.900 (+25%) | $44.400 | 55 |

Si los costos fijos suben 20% (CLP 2,88 millones), el punto de equilibrio del precio base sube a 84 clientes. Si el costo variable sube 20% (CLP 6.600), el equilibrio pasa a 73 clientes.

## Indicadores que conviene medir en un piloto

1. Conversión de prueba a cliente pagado y meses hasta primera compra.
2. Clientes activos, cancelación mensual y retención a 3/6/12 meses.
3. Ingreso recurrente mensual cobrado, descuento medio y morosidad.
4. Costo de adquisición por canal y meses para recuperar ese costo.
5. Horas de soporte por cliente, costo de infraestructura por cliente y disponibilidad.
6. Exactitud de stock, diferencias de conteo, quiebres y días de inventario.
7. Margen de contribución después de pagos, impuestos aplicables y soporte variable.

Como referencia hipotética, una cancelación mensual de 2% y contribución de $34.400 darían un LTV simplificado de $1.720.000 ($34.400 / 0,02), sin descuento temporal. A un CAC de $180.000, LTV/CAC sería 9,6× y CAC payback, 5,2 meses. **Estos valores son metas/supuestos para probar, no datos observados**; una vida de cliente larga o un costo de adquisición bajo no deben asumirse sin cohortes reales.

## Riesgos, exclusiones y próximos pasos económicos

- Validar el segmento, disposición a pagar y costos de alternativas mediante entrevistas y pilotos pagados.
- Definir si el precio es por local, empresa, usuarios o volumen; un local con varios usuarios cambia soporte e infraestructura.
- Cotizar nube y pasarela de pago en Chile; considerar variación del dólar, IVA, facturación y privacidad.
- Probar integración con POS/ERP solo con clientes que demuestren su costo y beneficio.
- Crear presupuesto mensual de caja con contrataciones, contingencia de ventas, capital de trabajo, churn y costo de adquisición.
- Revisar controles de acceso, respaldos restaurables, auditoría, monitoreo y política de retención antes de cargar datos reales.
- Separar margen bruto, EBITDA aproximado, resultado tributario y flujo de caja en un modelo contable posterior.

### Límites de este informe

Es un ejercicio de planificación sin investigación de precios de proveedores, entrevistas, cotizaciones, datos contables ni métricas históricas de ventas. No constituye asesoría financiera, tributaria o legal. Las cifras están expresadas en CLP nominales y no incluyen inflación, costo de capital ni valor presente neto; el ROI se mueve significativamente si cambian adquisición, precio, retención, dedicación del equipo o alcance funcional.
