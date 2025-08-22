import sys
import os
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from mp_api.client import MPRester
from pymatgen.analysis.diffraction.xrd import XRDCalculator


CONFIGURACION = {
    "NOMBRE_ARCHIVO": "sincompos.xrdml",
    "API_KEY": os.getenv("MP_API_KEY"), # ¡Asegúrate de poner tu clave aquí!
    "PROMINENCIA_PICO": 100.0,
    "LAMBDA_RAYOS_X_STR": "CoKa",
    "TOLERANCIA_ANGULO": 0.55,
    "SCORE_THRESHOLD": 2.0, 
    "NUMERO_MAX_FASES": 10,
    # Solo se considerarán fases con una energía por encima del casco inferior a este valor (en eV/átomo).
    # 0.05 es un buen valor para incluir fases estables y ligeramente metaestables.
    "STABILITY_THRESHOLD_EV_PER_ATOM": 0.05,
}

# 
def leer_xrdml_moderno(ruta_archivo):
    try:
        namespaces = {'xrdml': 'http://www.xrdml.com/XRDMeasurement/2.3'}
        tree = ET.parse(ruta_archivo)
        root = tree.getroot()
        counts_string = root.find('.//xrdml:counts', namespaces).text
        intensidades = np.array([float(c) for c in counts_string.strip().split()])
        pos_element = root.find('.//xrdml:positions[@axis="2Theta"]', namespaces)
        start_pos = float(pos_element.find('xrdml:startPosition', namespaces).text)
        end_pos = float(pos_element.find('xrdml:endPosition', namespaces).text)
        angulos = np.linspace(start_pos, end_pos, len(intensidades))
        return {'2theta': angulos, 'intensity': intensidades}
    except Exception as e:
        print(f"ERROR al leer '{os.path.basename(ruta_archivo)}': {e}")
        return None

class InteractivePhaseIdentifier:
    def __init__(self, config, mpr_connection):
        self.config = config
        self.mpr = mpr_connection
        self.xrd_calculator = XRDCalculator(wavelength=config["LAMBDA_RAYOS_X_STR"])

    def search_and_score(self, elements, exp_peaks):
        print(f"\nBuscando en Materials Project materiales con EXACTAMENTE los elementos: {elements}...")
        try:
            
            docs = self.mpr.materials.summary.search(
                elements=elements, num_elements=len(elements), 
                fields=["material_id", "formula_pretty", "structure", "energy_above_hull"]
            )
        except Exception as e:
            print(f"Error en la consulta a la API: {e}")
            return []

        if not docs:
            print("No se encontraron estructuras con esta combinación exacta de elementos.")
            return []
            
        
        stable_docs = [
            doc for doc in docs 
            if doc.energy_above_hull <= self.config["STABILITY_THRESHOLD_EV_PER_ATOM"]
        ]
        print(f"Se encontraron {len(docs)} candidatos. {len(stable_docs)} son estables y serán analizados.")

        if not stable_docs:
            print("Ninguno de los candidatos encontrados es termodinámicamente estable. No hay resultados para mostrar.")
            return []

        print(f"Calculando y puntuando los {len(stable_docs)} candidatos estables...")
        
        all_matches = []
        
        for doc in stable_docs:
            try:
                pattern = self.xrd_calculator.get_pattern(doc.structure, two_theta_range=(0,90))
                ref_thetas = pattern.x
                ref_intensities = (pattern.y / pattern.y.max()) * 100
                total_score = 0
                for exp_theta, exp_intensity in exp_peaks:
                    diffs = np.abs(ref_thetas - exp_theta)
                    closest_idx = np.argmin(diffs)
                    if diffs[closest_idx] <= self.config["TOLERANCIA_ANGULO"]:
                        intensity_score = 1.0 - abs(exp_intensity - ref_intensities[closest_idx]) / 100.0
                        total_score += intensity_score
                
                final_score = (total_score / len(exp_peaks)) * 100
                
                if final_score >= self.config["SCORE_THRESHOLD"]:
                    all_matches.append({
                        "id": doc.material_id, "score": final_score, 
                        "formula": doc.formula_pretty, "pattern": pattern
                    })
            except Exception:
                continue
        
        sorted_matches = sorted(all_matches, key=lambda x: x['score'], reverse=True)
        return sorted_matches


def main():
    config = CONFIGURACION
    if len(sys.argv) > 1:
        config["NOMBRE_ARCHIVO"] = sys.argv[1]

    datos = leer_xrdml_moderno(config["NOMBRE_ARCHIVO"])
    if not datos: return
    
    indices_picos, _ = find_peaks(datos['intensity'], prominence=config["PROMINENCIA_PICO"])
    if len(indices_picos) == 0:
        print("No se encontraron picos iniciales. Ajusta 'PROMINENCIA_PICO'.")
        return

    all_peaks = list(zip(datos['2theta'][indices_picos], datos['intensity'][indices_picos]))
    all_peaks.sort(key=lambda x: x[1], reverse=True)
    
    all_intensities = np.array([p[1] for p in all_peaks])
    all_intensities_norm = (all_intensities / all_intensities.max()) * 100
    all_thetas = np.array([p[0] for p in all_peaks])
    peaks_for_scoring = list(zip(all_thetas, all_intensities_norm))

    identified_phases = []
    
    try:
        with MPRester(config["API_KEY"]) as mpr:
            identifier = InteractivePhaseIdentifier(config, mpr)

            for i in range(config["NUMERO_MAX_FASES"]):
                print("\n\n" + "="*57)
                print(f"      ITERACIÓN DE BÚSQUEDA #{i + 1}")
                print("="*57)

                top_peaks_df = pd.DataFrame(all_peaks[:5], columns=["2-Theta (°)", "Intensidad (abs)"])
                print("Picos más fuertes del patrón completo:")
                print(top_peaks_df.to_string(index=False, float_format="%.2f"))
                
                if identified_phases:
                    print("\n--- Fases ya Identificadas ---")
                    for phase in identified_phases:
                        print(f"  - {phase['formula']} (Score: {phase['score']:.2f}%)")
                    print("------------------------------")

                print("\nBasado en los picos, sugiere una familia química.")
                user_input = input("Elementos a buscar (separados por coma, o 'saltar'/'salir'): ").strip()

                if user_input.lower() in ['salir', 'quit', 'exit']: break
                if user_input.lower() in ['saltar', 'skip']: continue
                
                elements_to_search = [elem.strip().capitalize() for elem in user_input.split(',')]
                if not all(elements_to_search):
                    print("Entrada no válida.")
                    continue
                
                best_matches = identifier.search_and_score(elements_to_search, peaks_for_scoring)
                
                if best_matches:
                    print("\n¡Posibles Coincidencias Encontradas (solo fases estables)!")
                    
                    df_results = pd.DataFrame(best_matches, columns=['score', 'formula', 'id'])
                    df_results.index = np.arange(1, len(df_results) + 1)
                    print(df_results.to_string(float_format="%.2f"))
                    
                    try:
                        choice = input("\nAceptar fase # (o presiona Enter para saltar): ").strip()
                        if not choice: continue
                        
                        selection = int(choice)
                        if 1 <= selection <= len(best_matches):
                            selected_phase = best_matches[selection - 1]
                            
                            identified_phases.append({
                                'id': selected_phase['id'],
                                'score': selected_phase['score'],
                                'formula': selected_phase['formula']
                            })
                            print(f"Fase '{selected_phase['formula']}' aceptada y registrada.")
                        else:
                            print("Selección fuera de rango.")
                    except ValueError:
                        print("Entrada no válida. Se esperaba un número.")
                else:
                    print(f"No se encontró ninguna coincidencia estable para '{', '.join(elements_to_search)}' que superara el umbral.")

    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

    print("\n\n" + "="*45)
    print(f"      RESULTADO FINAL DEL ANÁLISIS")
    print("="*45)
    if identified_phases:
        print(f"Se identificaron las siguientes fases en '{config['NOMBRE_ARCHIVO']}':\n")
        df = pd.DataFrame(identified_phases)
        print(df.to_string(index=False, float_format="%.2f"))
    else:
        print("No se identificó ninguna fase.")

if __name__ == '__main__':

    main()
