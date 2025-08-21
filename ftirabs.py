import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
from matplotlib.ticker import MultipleLocator

def comparar_espectros_crudo(archivos_entrada, nombre_salida):
    """
    Lee múltiples archivos de espectro infrarrojo y los grafica juntos
    utilizando los datos en crudo, sin normalización.

    Args:
        archivos_entrada (list): Una lista de rutas a los archivos de datos .txt.
        nombre_salida (str): El nombre del archivo de imagen para guardar la gráfica.
    """
    plt.figure(figsize=(15, 8))
    
    x_units = "1/CM"
    y_units = "%T" # Valor por defecto

    for ruta_archivo in archivos_entrada:
        try:
            # Leer las unidades de las primeras líneas del archivo
            with open(ruta_archivo, 'r') as f:
                lines = f.readlines()
                # Se busca en las primeras 10 líneas para eficiencia
                for line in lines[:10]: 
                    if line.startswith('##XUNITS='):
                        x_units = line.strip().split('=')[1]
                    elif line.startswith('##YUNITS='):
                        y_units = line.strip().split('=')[1]

            # Leer los datos numéricos usando pandas
            data = pd.read_csv(
                ruta_archivo,
                comment='#',
                sep=r'\s+',
                header=None,
                names=['x', 'y']
            )

           
            nombre_muestra = os.path.basename(ruta_archivo).replace('.txt', '')
            
            # Dibujar la gráfica con los datos en crudo (columna 'y')
            plt.plot(data['x'], data['y'], label=nombre_muestra)

        except FileNotFoundError:
            print(f"Advertencia: El archivo '{ruta_archivo}' no fue encontrado. Se omitirá.")
        except Exception as e:
            print(f"Ocurrió un error al procesar '{ruta_archivo}': {e}")

    # --- CAMBIOS EN LA GRÁFICA ---
    # 1. Títulos y etiquetas actualizados para reflejar los datos en crudo
    plt.title('Comparación de Espectros Infrarrojos (Datos en Crudo)')
    plt.xlabel(f'Número de Onda ({x_units})')
    plt.ylabel(f'{y_units}') # Se usa la unidad leída del archivo (%T, Abs, etc.)
    
    # Invertir el eje X, estándar para espectros IR
    ax = plt.gca()
    ax.invert_xaxis()
    
    # Configurar una cuadrícula detallada
    # Para el eje X (Número de Onda)
    ax.xaxis.set_major_locator(MultipleLocator(200))
    ax.xaxis.set_minor_locator(MultipleLocator(50))

    # 2. Se eliminan los localizadores del eje Y para que Matplotlib los ajuste automáticamente
    #    a la escala de los datos de transmitancia/absorbancia.

    # Activar la cuadrícula
    ax.grid(which='both', linestyle='-', linewidth='0.5')
    ax.grid(which='minor', axis='x', linestyle=':', linewidth='0.5', color='lightgray')

    plt.legend()
    # Guardar la gráfica con el formato del nombre de archivo (ej. .png o .jpg)
    plt.savefig(nombre_salida, dpi=300)
    print(f"¡Listo! Gráfica guardada en: {nombre_salida}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        # Instrucciones de uso actualizadas
        print("\nUso: python ftirabs.py <grafica.png> <archivo1.txt> <archivo2.txt> ...")
        print("\nEjemplo:")
        print("python ftirabs.py mi_comparacion_cruda.png ftir/prueba1.txt ftir/prueba2.txt")
    else:
        archivo_salida = sys.argv[1]
        archivos_entrada = sys.argv[2:]
        comparar_espectros_crudo(archivos_entrada, archivo_salida)