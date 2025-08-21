import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
from matplotlib.ticker import MultipleLocator
import xml.etree.ElementTree as ET
import numpy as np # Necesario para calcular los ángulos

def leer_xrdml_moderno(ruta_archivo):
    """
    Lee un archivo XRDML v2.3 que usa start/end position para los ángulos.
    """
    try:
        # Definimos el 'namespace' correcto para la versión 2.3 del archivo
        namespaces = {'xrdml': 'http://www.xrdml.com/XRDMeasurement/2.3'}
        
        tree = ET.parse(ruta_archivo)
        root = tree.getroot()
        
        # 1. Extraer las intensidades (counts)
        counts_string = root.find('.//xrdml:counts', namespaces).text
        intensidades = [float(c) for c in counts_string.strip().split()]
        
        # 2. Extraer las posiciones de inicio y fin
        pos_element = root.find('.//xrdml:positions[@axis="2Theta"]', namespaces)
        start_pos = float(pos_element.find('xrdml:startPosition', namespaces).text)
        end_pos = float(pos_element.find('xrdml:endPosition', namespaces).text)
        
        # 3. Calcular el eje de ángulos 2-Theta
        num_puntos = len(intensidades)
        angulos = np.linspace(start_pos, end_pos, num_puntos)
        
        print(f"  -> Lectura exitosa de '{os.path.basename(ruta_archivo)}'. Se encontraron {num_puntos} puntos.")
        return {'2theta': angulos, 'intensity': intensidades}

    except Exception as e:
        print(f"  -> ERROR al leer '{os.path.basename(ruta_archivo)}': {e}")
        return None


def comparar_difractogramas(archivos_entrada, nombre_salida):
    plt.figure(figsize=(15, 8))
    archivos_procesados_exitosamente = 0

    for ruta_archivo in archivos_entrada:
        print(f"\nProcesando archivo: '{ruta_archivo}'")
        xrd_data = leer_xrdml_moderno(ruta_archivo)

        if xrd_data:
            data = pd.DataFrame({
                'x': xrd_data['2theta'],
                'y': xrd_data['intensity']
            })

            y_min = data['y'].min()
            y_max = data['y'].max()
            data['y_norm'] = (data['y'] - y_min) / (y_max - y_min)

            nombre_muestra = os.path.basename(ruta_archivo).split('.')[0]
            plt.plot(data['x'], data['y_norm'], label=nombre_muestra)
            archivos_procesados_exitosamente += 1

    if archivos_procesados_exitosamente > 0:
        plt.title('Comparación de Difractogramas (Intensidad Normalizada)')
        plt.xlabel('Ángulo 2-Theta (°)')
        plt.ylabel('Intensidad Normalizada')
        ax = plt.gca()
        ax.xaxis.set_major_locator(MultipleLocator(10))
        ax.xaxis.set_minor_locator(MultipleLocator(2.5))
        ax.yaxis.set_major_locator(MultipleLocator(0.1))
        ax.yaxis.set_minor_locator(MultipleLocator(0.05))
        ax.grid(which='both', linestyle='-', linewidth='0.5')
        ax.grid(which='minor', linestyle=':', linewidth='0.5', color='lightgray')
        plt.legend()
        plt.savefig(nombre_salida, format='jpg', dpi=300)
        print(f"\n¡Listo! Gráfica con {archivos_procesados_exitosamente} muestra(s) guardada en: {nombre_salida}")
    else:
        print("\nOperación cancelada: No se pudo procesar ningún archivo de entrada válido.")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("\nUso: python comparar_xrd_final.py <salida.jpg> <archivo1.xrdml> ...")
    else:
        archivo_salida = sys.argv[1]
        archivos_entrada = sys.argv[2:]
        comparar_difractogramas(archivos_entrada, archivo_salida)