import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def click_xpath(wait, xpath, pausa=1):
    """Hace clic en un elemento cuando esté disponible."""
    btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    btn.click()
    time.sleep(pausa)

def obtener_datos():
    # Configurar navegador
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 30)

    try:
        driver.get("https://prod2.seace.gob.pe/seacebus-uiwd-pub/buscadorPublico/buscadorPublico.xhtml")

        # Buscar entidad PRONIED
        click_xpath(wait, '//*[@id="tbBuscador"]/ul/li[2]/a', pausa=3)
        click_xpath(wait, '//a[@id="tbBuscador:idFormBuscarProceso:ajax"]', pausa=3)

        search_box = wait.until(EC.element_to_be_clickable((By.ID, "tbBuscador:idFormBuscarProceso:txtNombreEntidad")))
        search_box.send_keys("pronied")

        click_xpath(wait, '//button[@id="tbBuscador:idFormBuscarProceso:btnBuscarEntidad"]', pausa=3)
        click_xpath(wait, '//a[@id="tbBuscador:idFormBuscarProceso:dataTable:0:ajax"]', pausa=3)
        click_xpath(wait, '//button[@id="tbBuscador:idFormBuscarProceso:btnBuscarSelToken"]', pausa=4)

        data = []
        page = 1

        while True:
            print(f"📄 Procesando página {page}...")

            # Esperar la tabla
            table = wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="tbBuscador:idFormBuscarProceso:dtProcesos"]/div[1]/table/tbody')
            ))
            rows = table.find_elements(By.TAG_NAME, "tr")

            for i in range(len(rows)):
                    try:
                        # Reobtenemos cada fila al inicio (evita referencias obsoletas)
                        table = wait.until(EC.presence_of_element_located(
                            (By.XPATH, '//*[@id="tbBuscador:idFormBuscarProceso:dtProcesos"]/div[1]/table/tbody')))
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        row = rows[i]
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if not cols:
                            continue

                        fila = {
                            "N°": cols[0].text.strip(),
                            "Entidad": cols[1].text.strip(),
                            "Fecha Publicación": cols[2].text.strip(),
                            "Nomenclatura": cols[3].text.strip(),
                            "Reiniciado Desde": cols[4].text.strip(),
                            "Objeto Contratación": cols[5].text.strip(),
                            "Descripción Objeto": cols[6].text.strip(),
                            "Código SNP": cols[7].text.strip(),
                            "Código Único Inversión": cols[8].text.strip(),
                            "VR/VE": cols[9].text.strip(),
                            "Moneda": cols[10].text.strip(),
                            "Versión SEACE": cols[11].text.strip(),
                            "Cronograma": []
                        }

                        # Intentar abrir el cronograma
                        try:
                            links = cols[-1].find_elements(By.TAG_NAME, "a")
                            if len(links) >= 2:
                                links[1].click()
                                time.sleep(3)

                                cronograma_rows = driver.find_elements(
                                    By.XPATH, '//*[@id="tbFicha:dtCronograma_data"]/tr'
                                )
                                for crow in cronograma_rows:
                                    ccols = crow.find_elements(By.TAG_NAME, "td")
                                    if len(ccols) >= 3:
                                        fila["Cronograma"].append({
                                            "Etapa": ccols[0].text.strip(),
                                            "Fecha Inicio": ccols[1].text.strip(),
                                            "Fecha Fin": ccols[2].text.strip()
                                        })

                                # Volver atrás
                                click_xpath(wait, '//*[@id="tbFicha:j_idt22"]', pausa=2)

                        except Exception as e:
                            print(f"Error al abrir cronograma fila {i}: {e}")

                        data.append(fila)

                    except Exception as e:
                        print(f"Error procesando fila {i}: {e}")
                        continue

            # --- PAGINACIÓN ---
            try:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

                paginator = wait.until(EC.presence_of_element_located((
                    By.ID, "tbBuscador:idFormBuscarProceso:dtProcesos_paginator_bottom"
                )))

                next_button = paginator.find_element(By.CLASS_NAME, "ui-paginator-next")

                if "ui-state-disabled" in next_button.get_attribute("class"):
                    print("✅ Última página alcanzada.")
                    break

                # Obtener número de página actual antes del cambio
                current_page = paginator.find_element(By.CLASS_NAME, "ui-paginator-current").text

                # Click en “Siguiente”
                driver.execute_script("arguments[0].click();", next_button)
                print("➡️ Pasando a la siguiente página...")
                time.sleep(3)

                # Esperar a que cambie la página
                wait.until_not(EC.text_to_be_present_in_element(
                    (By.CLASS_NAME, "ui-paginator-current"), current_page
                ))

                page += 1

            except Exception as e:
                print(f"⚠️ Error al intentar pasar de página: {e}")
                break

        # Guardar resultados
        with open("procesos_pronied_con_cronograma.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"✅ Datos guardados ({len(data)} registros).")

    except Exception as e:
        print(f"❌ Error en la búsqueda: {e}")

if __name__ == "__main__":
    obtener_datos()
