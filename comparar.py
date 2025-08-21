import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
from matplotlib.ticker import MultipleLocator

def comparar_espectros(archivos_entrada, nombre_salida):
    """
    Lee múltiples archivos de espectro infrarrojo y los grafica juntos.

    Args:
        archivos_entrada (list): Una lista de rutas a los archivos de datos .txt.
        nombre_salida (str): El nombre del archivo de imagen para guardar la gráfica.
    """
    plt.figure(figsize=(15, 8))
    
    x_units = "1/CM"
    y_units = "%T"

    for ruta_archivo in archivos_entrada:
        try:
            # Leer las unidades de las primeras líneas del archivo (solo para la primera gráfica)
            with open(ruta_archivo, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('##XUNITS='):
                        x_units = line.strip().split('=')[1]
                    elif line.startswith('##YUNITS='):
                        y_units = line.strip().split('=')[1]
                    elif not line.startswith('##'):
                        break

            # Leer los datos numéricos usando pandas
            data = pd.read_csv(
                ruta_archivo,
                comment='#',
                sep=r'\s+',
                header=None,
                names=['x', 'y']
            )

            # Normalización Min-Max de los datos de transmitancia (eje Y)
            y_min = data['y'].min()
            y_max = data['y'].max()
            data['y_norm'] = (data['y'] - y_min) / (y_max - y_min)

            # Extraer el nombre de la muestra del nombre del archivo para la leyenda
            nombre_muestra = os.path.basename(ruta_archivo).replace('.txt', '')
            
            # Dibujar la gráfica con los datos normalizados
            plt.plot(data['x'], data['y_norm'], label=nombre_muestra)

        except FileNotFoundError:
            print(f"Advertencia: El archivo '{ruta_archivo}' no fue encontrado. Se omitirá.")
        except Exception as e:
            print(f"Ocurrió un error al procesar '{ruta_archivo}': {e}")

    # Añadir títulos y etiquetas
    plt.title('Comparación de Espectros Infrarrojos (Normalizados)')
    plt.xlabel(f'Número de Onda ({x_units})')
    plt.ylabel(f'Intensidad Normalizada')
    
    # Invertir el eje X
    ax = plt.gca()
    ax.invert_xaxis()
    
    # Configurar una cuadrícula más detallada
    # Para el eje X (Número de Onda)
    ax.xaxis.set_major_locator(MultipleLocator(200))
    ax.xaxis.set_minor_locator(MultipleLocator(50))

    # Para el eje Y (Intensidad Normalizada)
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.yaxis.set_minor_locator(MultipleLocator(0.05))

    # Activar la cuadrícula para ambas divisiones
    ax.grid(which='both', linestyle='-', linewidth='0.5')
    ax.grid(which='minor', linestyle=':', linewidth='0.5', color='lightgray')

    plt.legend()
    plt.savefig(nombre_salida)
    print(f"lito:) {nombre_salida}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("python comparar.py grafica.png ftir/prueba1.txt ftir/prueba2.txt")
    else:
        archivo_salida = sys.argv[1]
        archivos_entrada = sys.argv[2:]
        comparar_espectros(archivos_entrada, archivo_salida)
