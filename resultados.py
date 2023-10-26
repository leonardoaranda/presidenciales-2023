import json
import requests
import os
import sys
import pandas
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('elecciones')



class Resultados():

    JSON_PATH = 'data/jsons/'
    NOMENCLATOR_PATH = 'data/nomenclator.json'

    def __init__(self):
        self.save()
        self.load()

    def save(self):
        """
        Descarga un objeto json desde la pagina de la Direccion Nacional Electoral que 
        contiene el listado de todos los IDs de las mesas
        """
        if not os.path.isfile(self.NOMENCLATOR_PATH):
            response = requests.get('https://resultados.gob.ar/backend-difu/nomenclator/getNomenclator')
            nomenclator = response.text
            with open(self.NOMENCLATOR_PATH, 'w') as f:
                f.write(nomenclator)

    def load(self):
        """
        Lee el archivo JSON que contiene todos los ids de mesas
        """
        if os.path.isfile(self.NOMENCLATOR_PATH):
            self.data = json.loads(open(self.NOMENCLATOR_PATH, 'r').read())

    def elecciones(self):
        """
        Imprime el listado de elecciones posibles analizar
        """
        return self.data['elec']

    def mesas(self):
        """
        Los resultados estan ordenados. En la posicion 13 se encuentran los resultados
        para las elecciones presidenciales. L = 8 corresponde a las mesas
        """
        ambitos = pandas.DataFrame(self.data['amb'][13]['ambitos'])
        return ambitos[ambitos['l'] == 8].copy()

    def download(self, mesas, frac=1):
        """
        Obtiene el resultado de votos de cada una de las mesas

        Parameters
        ----------
        mesas : pandas.DataFrame
            Es un dataframe que contiene las mesas a descargar
            se obtiene a partir de Resultados.mesas()
        frac :
            Muestra a descargar. Si no es especificado, descarga
            el 0.1% de las mesas del dataframe.
        """

        mesas = mesas.sample(frac=0.001)
        logger.info('Cantidad de mesas a descargar '+str(mesas.shape[0]))
        for i, r in mesas.iterrows():
            try:
                if r['co'][-1] != 'E':
                    url = 'https://resultados.gob.ar/backend-difu/scope/data/getScopeData/' + r['co'] + '/1'
                    d = requests.get(url)
                    votos = d.json()
                    id = votos['id']['idAmbito']['codigo']
                    with open('data/jsons/'+id+'.json', 'w') as outfile:
                        json_object = json.dumps(votos, indent=4)
                        outfile.write(json_object)
            except Exception as e:
                with open('data/errors/ids.txt', 'a') as outfile_e:
                    outfile_e.write(r['co']+'\n')
                logger.error('error en la mesa: ', r['co'], e)
        logger.info('Se descargaron todas las mesas')

    def export(self):
        """
        Concatena los archivos JSON descargados y los guarda en un CSV.
        """
        mesas = []
        for archivo in os.listdir(self.JSON_PATH):
            if archivo.split('.')[1] == 'json':
                mesa = json.loads(open(self.JSON_PATH+archivo).read())
                mesa['id_mesa'] = mesa['id']['idAmbito']['codigo']
                for father in mesa['fathers']:
                    mesa['level_'+str(int(father['level']))] = father['name']
                for partido in mesa['partidos']:
                    mesa['partido_code'] = partido['code']
                    mesa['partido_name'] = partido['name']
                    mesa['partido_votos'] = partido['votos']
                    mesa['partido_perc'] = partido['perc']
                    mesa['partido_percCarg'] = partido['percCarg']
                    mesa['partido_cargos'] = partido['cargos']
                    mesa['partido_candidatos'] = ' - '.join(partido['candidatos'])
                    mesas.append(mesa.copy())
        pandas.DataFrame(mesas).to_csv('data/data.csv', index=False)
        logger.info('Se exportaron correctamente los resultados en data/data.csv')


if __name__ == '__main__':

    resultados = Resultados()
    mesas = resultados.mesas()
    resultados.download(mesas, float(sys.argv[1]))
    resultados.export()