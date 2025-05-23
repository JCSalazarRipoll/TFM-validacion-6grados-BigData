#************************************** Importando librerías *********************************************#
import networkx as nx
import requests
import gzip
import shutil
import random
import numpy as np
import warnings
import unittest
from typing import Dict, Tuple, List, Callable, Optional
import matplotlib.pyplot as plt
import itertools
import logging
import pickle
import os
from tqdm import tqdm
from torch_geometric.data import Data
import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, global_mean_pool
from torch.nn import Linear
import torch.nn as nn
import random
import torch
import torch.nn as nn
import numpy as np
from typing import List, Callable
import copy
from sortedcontainers import SortedList
from networkx.drawing.nx_agraph import graphviz_layout

#************************************** Definición de clases *********************************************#

class Gene:
    """
    Clase que define un Gen en un Genoma.

    Attributes
    ----------
    gene_id : int
        ID del gen.
    gene_type : str
        Tipo de gen ('input', 'hidden' o 'output').
    innovation_number : int
        Número de innovación asociado al gen.
          
    Methods
    -------
    __repr__():
        Devuelve una representación en cadena del gen.
    """

    def __init__(self, gene_id: int, gene_type: str, innovation_number: int = None):
        """
        Inicializa un Gen.

        Attributes
        ----------
        gene_id : int
            Identificación única del gen.
        gene_type : str
            Tipo del gen ('input', 'hidden', 'output').
        innovation_number : int, opcional
            Número único de innovación.  Se usa para rastrear la historia evolutiva de los genes.
            Si no se proporciona, se asume que es igual a gene_id.
        """
        self.gene_id = gene_id
        self.gene_type = gene_type
        self.innovation_number = innovation_number if innovation_number is not None else gene_id  # Valor por defecto

    def __repr__(self) -> str:
        """
        Representación en cadena del gen.

        Returns
        -------
        str
            Representación en formato "Gene(id=..., type=..., innovation=...)".
        """
        return f"Gene(id={self.gene_id}, type={self.gene_type}, innovation={self.innovation_number})"

class ConnectionGene:
    """
    Clase que define un Gen de Conexión en un Genoma.

    Parameters
    ----------
    in_node_id : int
        ID del nodo de entrada.
    out_node_id : int
        ID del nodo de salida.
    weight : float
        Peso asignado a la conexión.
    enabled : bool
        Indica si la conexión está habilitada.
    innovation_number : int
        Número único de innovación de la conexión.

    Attributes
    ----------
    in_node_id : int
        ID del nodo de entrada de la conexión.
    out_node_id : int
        ID del nodo de salida de la conexión.
    weight : float
        Peso de la conexión.
    enabled : bool
        Indica si la conexión está activa.
    innovation_number : int, opcional
        Número único de innovación para esta conexión.

    Methods
    -------
    __init__(in_node_id, out_node_id, weight, enabled, innovation_number)
        Inicializa un Gen de Conexión.
    __repr__()
        Devuelve una representación en cadena del gen de conexión.
    """
    def __init__(self, in_node_id: int, out_node_id: int, weight: float, enabled: bool, innovation_number: int):
        """
        Inicializa un Gen de Conexión.

        Attributes
        ----------
        in_node_id : int
            ID del nodo de entrada de la conexión.
        out_node_id : int
            ID del nodo de salida de la conexión.
        weight : float
            Peso de la conexión.
        enabled : bool
            Indica si la conexión está activa.
        innovation_number : int
            Número único de innovación para esta conexión.
        """
        self.in_node_id = in_node_id
        self.out_node_id = out_node_id
        self.weight = weight
        self.enabled = enabled
        self.innovation_number = innovation_number

    def __repr__(self) -> str:
        """
        Representación en cadena de la conexión.

        Returns
        -------
        str
            Representación en formato "ConnectionGene(in=..., out=..., weight=..., enabled=..., innovation=...)".
        """
        return f"ConnectionGene(in={self.in_node_id}, out={self.out_node_id}, weight={self.weight:.2f}, enabled={self.enabled}, innovation={self.innovation_number})"

class ConnectionMatrix:
    """
    Clase para gestionar dinámicamente una matriz de conexiones booleanas entre nodos.

    Attributes
    ----------
    matriz : numpy.ndarray
        Matriz de adyacencia de conexiones booleanas.
    nodo_a_indice : dict
        Mapeo de IDs de nodos a índices de la matriz.
    indice_a_nodo : dict
        Mapeo inverso de índices a IDs de nodos.
    siguiente_indice : int
        Índice disponible para el próximo nodo agregado.
    nodos : set
        Conjunto de IDs de nodos presentes.

    Methods
    -------
    agregar_nodo(nodo_id)
        Agrega un nuevo nodo a la matriz.
    agregar_conexion(nodo_desde, nodo_hasta)
        Agrega una conexión entre dos nodos existentes.
    eliminar_conexiones_nodo(nodo_id)
        Elimina todas las conexiones asociadas a un nodo.
    eliminar_nodo(nodo_id)
        Elimina un nodo y sus conexiones.
    existe_conexion(nodo_desde, nodo_hasta)
        Verifica si existe una conexión entre dos nodos.
    obtener_matriz()
        Devuelve la matriz actual de conexiones.
    modificar_conexiones_nodo(nodo_id, nuevas_conexiones_entrantes, nuevas_conexiones_salientes)
        Modifica las conexiones entrantes y salientes de un nodo.
    conexiones_entrantes(nodo_id)
        Devuelve una lista de nodos que tienen conexiones hacia un nodo dado.
    conexiones_salientes(nodo_id)
        Devuelve una lista de nodos a los que un nodo dado está conectado.
    """

    def __init__(self):
        """
        Inicializa la matriz de conexiones.
        """
        self.matriz = np.empty((0, 0), dtype=bool)  # Inicializa con una matriz vacía
        self.nodo_a_indice = {}  # Mapeo de ID de nodo a índice de matriz
        self.indice_a_nodo = {}  # Mapeo de índice de matriz a ID de nodo
        self.siguiente_indice = 0  # Índice para el próximo nodo a agregar
        self.nodos = set()  # Conjunto para guardar los IDs de los nodos presentes

    def reindexar_nodos(self):
        """
        Reindexa los nodos y redimensiona la matriz.

        Este método se llama internamente para asegurar que los índices de la matriz
        correspondan a los IDs de los nodos después de agregar o eliminar nodos.
        """
        nodos_ordenados = sorted(list(self.nodos))  # Ordena la lista de nodos
        nuevo_tamano = len(nodos_ordenados)  # Se redimensionará la matriz
        nueva_matriz = np.zeros((nuevo_tamano, nuevo_tamano), dtype=bool)  # Nueva matriz booleana
        nuevo_nodo_a_indice = {}  # Se creará una nueva lista de nodos a índices
        nuevo_indice_a_nodo = {}  # Se creará una nueva lista de índices a nodos

        for i, nodo_id in enumerate(nodos_ordenados):  # Se van a actualizar las listas
            nuevo_nodo_a_indice[nodo_id] = i
            nuevo_indice_a_nodo[i] = nodo_id

        # Se recorre la vieja matriz, buscando en los indices los nuevos indices
        for indice_origen in range(len(self.matriz)):  # Se obtienen los indices origen
            for indice_destino in range(len(self.matriz)):  # Se obtienen los indices destino
                if self.matriz[indice_origen, indice_destino]:  # Si esta conexion existe en la matriz anterior
                    nodo_origen = self.indice_a_nodo[indice_origen]  # Se ubica el nodo correspondiente al origen
                    nodo_destino = self.indice_a_nodo[indice_destino]  # Se ubica el nodo correspondiente al destino
                    nuevo_indice_origen = nuevo_nodo_a_indice[nodo_origen]  # Se obtiene el nuevo indice origen
                    nuevo_indice_destino = nuevo_nodo_a_indice[nodo_destino]  # Se obtiene el nuevo indice destino
                    nueva_matriz[nuevo_indice_origen, nuevo_indice_destino] = True  # Se agrega la conexion a la nueva matriz

        self.matriz = nueva_matriz  # Se actualiza la matriz
        self.nodo_a_indice = nuevo_nodo_a_indice  # Se actualizan los diccionarios
        self.indice_a_nodo = nuevo_indice_a_nodo
        self.siguiente_indice = nuevo_tamano  # Se aumenta el siguiente indice

    def agregar_nodo(self, nodo_id: int) -> None:
        """
        Agrega un nuevo nodo a la matriz de conexiones.

        Parameters
        ----------
        nodo_id : int
            ID del nodo a agregar.
        """
        if nodo_id not in self.nodos:  # Solo agrega si no existe
            # Se agrega el nodo en los diccionarios
            self.nodo_a_indice[nodo_id] = self.siguiente_indice  # Se actualiza el diccionario
            self.indice_a_nodo[self.siguiente_indice] = nodo_id  # Se actualiza el diccionario
            self.siguiente_indice = self.siguiente_indice + 1  # Aumenta en 1 el siguiente índice
            self.nodos.add(nodo_id)  # Se agrea el nodo al conjunto de nodos
            self.reindexar_nodos()  # Se reindexan los nodos

    def agregar_conexion(self, nodo_desde: int, nodo_hasta: int) -> None:
        """
        Agrega una conexión dirigida entre dos nodos existentes.

        Parameters
        ----------
        nodo_desde : int
            ID del nodo de origen.
        nodo_hasta : int
            ID del nodo de destino.
        """
        if nodo_desde in self.nodos and nodo_hasta in self.nodos:
            indice_desde = self.nodo_a_indice[nodo_desde]  # Se obtiene el índice del origen
            indice_hasta = self.nodo_a_indice[nodo_hasta]  # Se obtiene el índice del destino
            self.matriz[indice_desde, indice_hasta] = True  # Se activa la conexión

    def eliminar_conexiones_nodo(self, nodo_id: int) -> None:
        """
        Elimina todas las conexiones asociadas a un nodo.

        Parameters
        ----------
        nodo_id : int
            ID del nodo a limpiar conexiones.
        """
        if nodo_id not in self.nodos:
            raise IndexError("El nodo no existe en la matriz.")
        indice = self.nodo_a_indice[nodo_id]
        self.matriz[indice, :] = False  # Elimina conexiones salientes
        self.matriz[:, indice] = False  # Elimina conexiones entrantes

    def eliminar_nodo(self, nodo_id: int) -> None:
        """
        Elimina un nodo y todas sus conexiones.

        Parameters
        ----------
        nodo_id : int
            ID del nodo a eliminar.
        """

        # Si el id del nodo se encuentra en la lista
        if nodo_id in self.nodos:
            # Si es el único nodo
            if len(self.nodos) == 1:
                self.matriz = np.empty((0, 0), dtype=bool)  # Se actualiza la matriz a una vacía
                self.nodo_a_indice = {}  # Diccionario vacío
                self.indice_a_nodo = {}  # Diccionario vacío
                self.siguiente_indice = 0  # Índice para el próximo nodo a agregar
                self.nodos = set()  # Conjunto para guardar los ids de los nodos presentes
            else:
                self.eliminar_conexiones_nodo(nodo_id)  # Elimina las conexiones del nodo
                self.nodos.remove(nodo_id)
                self.reindexar_nodos()

    def existe_conexion(self, nodo_desde: int, nodo_hasta: int) -> bool:
        """
        Verifica si existe una conexión de un nodo hacia otro.

        Parameters
        ----------
        nodo_desde : int
            ID del nodo de origen.
        nodo_hasta : int
            ID del nodo de destino.

        Returns
        -------
        bool
            True si existe la conexión, False si no.
        """
        if nodo_desde not in self.nodos or nodo_hasta not in self.nodos:
            return False
        indice_desde = self.nodo_a_indice[nodo_desde]
        indice_hasta = self.nodo_a_indice[nodo_hasta]
        return self.matriz[indice_desde, indice_hasta]

    def obtener_matriz(self) -> np.ndarray:
        """
        Devuelve la matriz actual de conexiones.

        Returns
        -------
        numpy.ndarray
            Matriz booleana de adyacencia.
        """
        return self.matriz

    def modificar_conexiones_nodo(self, nodo_id: int, nuevas_conexiones_entrantes: dict, nuevas_conexiones_salientes: dict) -> None:
        """
        Modifica todas las conexiones entrantes y salientes de un nodo dado.

        Parameters
        ----------
        nodo_id : int
            ID del nodo a modificar.
        nuevas_conexiones_entrantes : dict
            Diccionario {nodo_origen: True/False} para modificar conexiones entrantes.
        nuevas_conexiones_salientes : dict
            Diccionario {nodo_destino: True/False} para modificar conexiones salientes.
        """
        # Si el nodo pertenece
        if nodo_id in self.nodos:
            # Se obtiene el índice
            indice_nodo = self.nodo_a_indice[nodo_id]
            # Se recorre el diccionario de conexiones entrantes
            for nodo_conectado, valor_conexion in nuevas_conexiones_entrantes.items():
                # Si el nodo pertenece
                if nodo_conectado in self.nodos:
                    # Se obtiene el índice
                    indice_conectado = self.nodo_a_indice[nodo_conectado]
                    # Se modifica la conexión
                    self.matriz[indice_conectado, indice_nodo] = valor_conexion  # conexiones entrantes
            for nodo_conectado, valor_conexion in nuevas_conexiones_salientes.items():
                # Si el nodo pertenece
                if nodo_conectado in self.nodos:
                    # Se obtiene el índice
                    indice_conectado = self.nodo_a_indice[nodo_conectado]
                    # Se modifica la conexión
                    self.matriz[indice_nodo, indice_conectado] = valor_conexion  # conexiones salientes

    def conexiones_entrantes(self, nodo_id: int) -> list:
        """
        Devuelve una lista de nodos que tienen conexiones hacia el nodo dado.

        Parameters
        ----------
        nodo_id : int
            ID del nodo objetivo.

        Returns
        -------
        list
            Lista de IDs de nodos conectados al nodo.
        """
        if nodo_id not in self.nodos:
            return []
        indice_nodo = self.nodo_a_indice[nodo_id]
        nodos_entrantes = []
        for nodo_desde in self.nodos:
            indice_desde = self.nodo_a_indice[nodo_desde]
            if self.matriz[indice_desde, indice_nodo]:
                nodos_entrantes.append(nodo_desde)
        return nodos_entrantes

    def conexiones_salientes(self, nodo_id: int) -> list:
        """
        Devuelve una lista de nodos a los cuales el nodo dado tiene conexiones salientes.

        Parameters
        ----------
        nodo_id : int
            ID del nodo fuente.

        Returns
        -------
        list
            Lista de IDs de nodos destino.
        """
        if nodo_id not in self.nodos:
            return []
        indice_nodo = self.nodo_a_indice[nodo_id]
        nodos_salientes = []
        for nodo_hasta in self.nodos:
            indice_hasta = self.nodo_a_indice[nodo_hasta]
            if self.matriz[indice_nodo, indice_hasta]:
                nodos_salientes.append(nodo_hasta)
        return nodos_salientes

class FeedforwardGenome:
    """
    Represents the genome of a feedforward neural network with bias.
    """
    def __init__(self, genome_id: int, num_inputs: int, num_outputs: int, innovation_manager: 'InnovationManager', initial_hidden_nodes: int = 8):
        """
        Initializes a feedforward genome with bias.
        """
        self.genome_id = genome_id
        self.genes = {}  # {node_id: (type, activation, innovation_number, bias)}
        self.connections = {}  # {(in_node_id, out_node_id, innovation_number): weight}
        self.next_node_id = 0
        self.fitness = None
        self.innovation_manager = innovation_manager  # Store the innovation manager
        self.output_nodes = []

        # Create input nodes (no bias)
        for _ in range(num_inputs):
            innovation_number = innovation_manager.create_innovation("gene", self.next_node_id, None)
            self.genes[self.next_node_id] = ('input', 'identity', innovation_number)
            self.next_node_id += 1

        # Create initial hidden nodes with random bias
        for _ in range(initial_hidden_nodes):
            innovation_number = innovation_manager.create_innovation("gene", self.next_node_id, None)
            self.genes[self.next_node_id] = ('hidden', random.choice(['relu', 'sigmoid', 'tanh']), innovation_number, random.uniform(-1, 1))
            self.next_node_id += 1

        # Create output nodes with random bias
        self.output_nodes = []
        for _ in range(num_outputs):
            innovation_number = innovation_manager.create_innovation("gene", self.next_node_id, None)
            self.genes[self.next_node_id] = ('output', 'identity', innovation_number, random.uniform(-1, 1))
            self.output_nodes.append(self.next_node_id)
            self.next_node_id += 1

        # Create some initial random connections with innovation numbers
        for i in range(num_inputs + initial_hidden_nodes):
            out_node = random.choice(list(self.genes.keys()))
            if self.genes[i][0] != 'output' and self.genes[out_node][0] != 'input' and i != out_node:
                innovation_number = innovation_manager.create_innovation("connection", i, out_node)
                self.connections[(i, out_node, innovation_number)] = random.uniform(-1, 1)

    def add_node(self, new_type: str, activation: str = 'relu', innovation_number: int = None):
        """Se agrega un nuevo nodo"""
        if innovation_number is None:
            raise ValueError("Innovation number must be provided when adding a node.")
        initial_bias = random.uniform(-1, 1) if new_type != 'input' else 0
        self.genes[self.next_node_id] = (new_type, activation, innovation_number, initial_bias)
        self.next_node_id += 1
        return self.next_node_id - 1

    def add_connection(self, in_node_id: int, out_node_id: int, weight: float = None, innovation_number: int = None):
        """Adds a new connection or modifies an existing one."""
        if (in_node_id, out_node_id, innovation_number) not in self.connections:
            if innovation_number is None:
                raise ValueError("Innovation number must be provided when adding a connection.")
            self.connections[(in_node_id, out_node_id, innovation_number)] = weight if weight is not None else random.uniform(-1, 1)
            return True
        return False

    def evaluate_genome(self, graph_data: List[tuple[torch.Tensor, torch.Tensor]]):
        """Evalúa el fitness de este genoma en un conjunto de datos."""
        total_loss = 0.0
        for features, target in graph_data:
            network = self.create_pytorch_network(num_inputs=features.shape[0])
            network.eval()
            with torch.no_grad():
                prediction = network(features.unsqueeze(0))
                loss = log_mse_loss(prediction.squeeze(), target)
                total_loss += loss.item()
        self.fitness = -total_loss / len(graph_data)
        return self.fitness

    def mutate_weights(self, mutation_rate: float, weight_mutation_power: float = 0.1):
        """Mutates the weights of the connections."""
        for connection in self.connections:
            if random.random() < mutation_rate:
                self.connections[connection] += random.uniform(-weight_mutation_power, weight_mutation_power)

    def mutate_biases(self, mutation_rate: float, bias_mutation_power: float = 0.1):
        """Mutates the bias of the nodes (excluding input nodes)."""
        for node_id, gene_info in self.genes.items():
            if gene_info[0] != 'input' and len(gene_info) > 3 and random.random() < mutation_rate:
                activation, innovation, bias = gene_info[1], gene_info[2], gene_info[3]
                self.genes[node_id] = (gene_info[0], activation, innovation, bias + random.uniform(-bias_mutation_power, bias_mutation_power))

    def mutate_add_node(self, possible_in_nodes, possible_out_nodes, innovation_manager: 'InnovationManager'):
        """Adds a new hidden node by splitting an existing connection."""
        if self.connections:
            connection_to_split = random.choice(list(self.connections.keys()))
            weight = self.connections.pop(connection_to_split)
            in_node, out_node, original_innovation = connection_to_split

            new_node_id = self.next_node_id
            self.next_node_id += 1
            new_node_innovation = innovation_manager.create_innovation("gene", new_node_id, None)
            self.add_node('hidden', random.choice(['relu', 'sigmoid', 'tanh']), new_node_innovation)

            # Create the new connections
            innovation_in_to_new = innovation_manager.create_innovation("connection", in_node, new_node_id)
            self.add_connection(in_node, new_node_id, weight=1.0, innovation_number=innovation_in_to_new)

            innovation_new_to_out = innovation_manager.create_innovation("connection", new_node_id, out_node)
            self.add_connection(new_node_id, out_node, weight=weight, innovation_number=innovation_new_to_out)

    def mutate_add_connection(self, possible_in_nodes, possible_out_nodes, innovation_manager: 'InnovationManager'):
        """Adds a new connection between two previously unconnected nodes."""
        if possible_in_nodes and possible_out_nodes:
            in_node = random.choice(possible_in_nodes)
            out_node = random.choice(possible_out_nodes)

            # Ensure we don't create a connection that already exists
            connection_exists = any((in_n, out_n) == (in_node, out_node) for in_n, out_n, _ in self.connections.keys())
            # Basic check for feedforward (can be made more sophisticated)
            if in_node != out_node and not connection_exists and in_node < out_node:
                innovation_number = innovation_manager.create_innovation("connection", in_node, out_node)
                self.add_connection(in_node, out_node, innovation_number=innovation_number)

    def mutate_eliminate_node(self):
        """Elimina un nodo oculto y sus conexiones.
            """
        #Se piden los nodos ocultos del genoma.
        hidden_nodes = [node_id for node_id, info in self.genes.items() if info[0] == 'hidden']
        #si no hay, no se hace nada
        if not hidden_nodes:
            return 
            
        #Se mezclan los noodos ocultos para obtener al azar un nodo oculto
        random.shuffle(hidden_nodes)
        #Por cada uno de los nodos ocultos
        for node_id in hidden_nodes:
            # Se piden las listas de las conexiones del nodo 
            connected_in = [(in_node, out_node, innov) for (in_node, out_node, innov) in self.connections if out_node == node_id]
            connected_out = [(in_node, out_node, innov) for (in_node, out_node, innov) in self.connections if in_node == node_id]
            
            for conn in connected_in + connected_out:
                self.connections.pop(conn, None)
                
            del self.genes[node_id]
            
            return
       
    def mutate_eliminate_connection(self):
        """Safely eliminate a connection while preserving node connectivity."""
        connections = list(self.connections.items())
        random.shuffle(connections)

        for (in_node, out_node, innov), _ in connections:
        
            if in_node not in self.genes or out_node not in self.genes:
                continue
            # Temporarily remove
            backup_weight = self.connections.pop((in_node, out_node, innov))

            # Recheck orphan status
            in_has_other_outputs = any((n1 != in_node or n2 != out_node) and n1 == in_node for (n1, n2, _) in self.connections)
            out_has_other_inputs = any((n1 != in_node or n2 != out_node) and n2 == out_node for (n1, n2, _) in self.connections)

            # If removal causes orphaning of a hidden node, revert
            in_is_hidden = self.genes[in_node][0] == 'hidden'
            out_is_hidden = self.genes[out_node][0] == 'hidden'

            if (in_is_hidden and not in_has_other_outputs) or (out_is_hidden and not out_has_other_inputs):
                self.connections[(in_node, out_node, innov)] = backup_weight  # Revert
            else:
                self.prune_orphan_nodes()
                return  # Done

    def prune_orphan_nodes(self):
        """Elimina los nodos huérfanos que no tienen conexiones entrantes ni salientes."""
        orphan_nodes = []

        # Busca nodos sin conexiones entrantes ni salientes
        for node in list(self.genes.keys()):
            # Si el nodo no tiene conexiones entrantes ni salientes
            if not any(n1 == node for (n1, n2, _) in self.connections) and \
               not any(n2 == node for (n1, n2, _) in self.connections):
                orphan_nodes.append(node)

        # Elimina los nodos huérfanos
        for orphan in orphan_nodes:
            del self.genes[orphan]  # Elimina el nodo de los genes
            # También elimina las conexiones asociadas al nodo huérfano
            self.connections = {key: value for key, value in self.connections.items() if key[0] != orphan and key[1] != orphan}

    def prune_disconnected_inputs(self):
        """Ensures all input nodes are connected to at least one other node."""
        input_nodes = [node_id for node_id, info in self.genes.items() if info[0] == 'input']
        connected_sources = set(in_node for (in_node, _, _) in self.connections)

        for input_node in input_nodes:
            if input_node not in connected_sources:
                # Attempt reconnection — connect to a random hidden or output node
                targets = [node_id for node_id, info in self.genes.items() if info[0] in ('hidden', 'output')]
                if not targets:
                    continue
                target = random.choice(targets)
                innov = self.innovation_manager.create_innovation("connection", input_node, target)
                self.add_connection(input_node, target, innovation_number=innov)


    def activate(self, inputs):
        """Activates the neural network based on the genome with bias."""
        if len(inputs) != self.get_num_inputs():
            raise ValueError("Number of inputs must match the number of input nodes.")

        node_values = {}
        # Set input node values
        input_nodes = {node_id: index for index, (node_id, gene_info) in enumerate(self.genes.items()) if gene_info[0] == 'input'}
        for node_id, input_index in input_nodes.items():
            node_values[node_id] = inputs[input_index]

        # Activate nodes based on connections
        sorted_nodes = sorted(self.genes.keys()) # Process nodes in order of their ID
        for node_id in sorted_nodes:
            if self.genes[node_id][0] != 'input':
                incoming_sum = 0
                for (in_node, out_node, _), weight in self.connections.items():
                    if out_node == node_id and in_node in node_values:
                        incoming_sum += node_values[in_node] * weight

                # Add bias
                bias = self.genes[node_id][3] if len(self.genes[node_id]) > 3 else 0
                incoming_sum += bias

                activation_type = self.genes[node_id][1]
                if activation_type == 'relu':
                    node_values[node_id] = max(0, incoming_sum)
                elif activation_type == 'sigmoid':
                    node_values[node_id] = 1 / (1 + torch.exp(-torch.tensor(incoming_sum))).item()
                elif activation_type == 'tanh':
                    node_values[node_id] = torch.tanh(torch.tensor(incoming_sum)).item()
                elif activation_type == 'identity':
                    node_values[node_id] = incoming_sum

        # Collect output node values
        output_values = [node_values.get(node_id, 0) for node_id in self.output_nodes]
        return output_values

    def create_pytorch_network(self, num_inputs: int):
        class ModifiableNet(nn.Module):
            def __init__(self, num_inputs):
                super().__init__()
                self.fc1 = nn.Linear(num_inputs, 64)
                self.bn1 = nn.BatchNorm1d(64)
                self.relu1 = nn.ReLU()
                self.fc2 = nn.Linear(64, 32)
                self.bn2 = nn.BatchNorm1d(32)
                self.relu2 = nn.ReLU()
                self.fc3 = nn.Linear(32, 1)
                self._initialize_weights()

            def _initialize_weights(self):
                for m in self.modules():
                    if isinstance(m, nn.Linear):
                        nn.init.xavier_uniform_(m.weight)
                        nn.init.zeros_(m.bias) # Biases are initialized to zero here
                    elif isinstance(m, nn.BatchNorm1d):
                        nn.init.ones_(m.weight)
                        nn.init.zeros_(m.bias)

            def forward(self, x):
                x = self.fc1(x)
                x = self.bn1(x)
                x = self.relu1(x)
                x = self.fc2(x)
                x = self.bn2(x)
                x = self.relu2(x)
                x = self.fc3(x)
                return x

        model = ModifiableNet(num_inputs)

        with torch.no_grad():
            input_nodes = {node_id for node_id, gene_info in self.genes.items() if gene_info[0] == 'input'}
            hidden_nodes = {node_id for node_id, gene_info in self.genes.items() if gene_info[0] == 'hidden'}
            output_nodes = {node_id for node_id, gene_info in self.genes.items() if gene_info[0] == 'output'}

            for (in_node, out_node, _), weight in self.connections.items():
                if in_node in input_nodes and out_node < 64:
                    if 0 <= out_node < model.fc1.out_features and 0 <= in_node < model.fc1.in_features:
                        model.fc1.weight[out_node, in_node] = weight * 0.1
                elif in_node in hidden_nodes and 64 <= out_node < 96: # Roughly map to fc2
                    pass
                elif in_node in (hidden_nodes | input_nodes) and out_node in output_nodes:
                    pass

        return model

    def copy(self):
        """Creates a deep copy of the FeedforwardGenome with bias."""
        new_genome = FeedforwardGenome(
            genome_id=self.genome_id,
            num_inputs=self.get_num_inputs(),
            num_outputs=self.get_num_outputs(),
            innovation_manager=self.innovation_manager,
            initial_hidden_nodes=0
        )
        new_genome.genes = copy.deepcopy(self.genes)
        new_genome.connections = copy.deepcopy(self.connections)
        new_genome.next_node_id = self.next_node_id
        new_genome.fitness = self.fitness
        new_genome.output_nodes = copy.deepcopy(self.output_nodes)
        return new_genome

    def get_num_inputs(self):
        return sum(1 for _, gene_info in self.genes.items() if gene_info[0] == 'input')

    def get_num_outputs(self):
        return len(self.output_nodes)

    def get_num_hidden_nodes(self):
        return sum(1 for _, gene_info in self.genes.items() if gene_info[0] == 'hidden')

    def visualize_network2(self):
        """Visualizes the neural network structure using NetworkX and Matplotlib with bias info."""
        G = nx.DiGraph()

        # Add nodes to the graph
        for node_id, gene_info in self.genes.items():
            node_type = gene_info[0]
            activation = gene_info[1]
            innovation_number = gene_info[2]
            bias = gene_info[3] if len(gene_info) > 3 else 0  # Get bias if it exists

            label = f"{node_id}\n({node_type}"
            if node_type == 'hidden':
                label += f", {activation}, b={bias:.2f})"
            elif node_type == 'output':
                label += f", b={bias:.2f})"
            else:
                label += ")"
            G.add_node(node_id, label=label, type=node_type)

        # Add edges (connections) to the graph
        for (in_node, out_node, _), weight in self.connections.items():
            if in_node in self.genes and out_node in self.genes:
                G.add_edge(in_node, out_node, weight=f"{weight:.2f}")

        # Define node colors based on type
        node_colors = {'input': 'lightblue', 'hidden': 'lightgreen', 'output': 'lightcoral'}
        colors = [node_colors[data['type']] for node, data in G.nodes(data=True)]

        # Define layout for the graph 
        pos = nx.spring_layout(G)

        # Draw the nodes
        nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=800)

        # Draw the edges with weights as labels
        edge_labels = nx.get_edge_attributes(G, 'weight')
        nx.draw_networkx_edges(G, pos, arrows=True)
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

        # Draw the node labels
        labels = nx.get_node_attributes(G, 'label')
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)

        plt.title(f"Genome ID: {self.genome_id}")
        plt.show()
        
    def visualize_network(self):
        """Visualizes the neural network structure using NetworkX and Graphviz layout with bias info."""
        G = nx.DiGraph()

        # Add nodes to the graph
        for node_id, gene_info in self.genes.items():
            node_type = gene_info[0]
            activation = gene_info[1]
            innovation_number = gene_info[2]
            bias = gene_info[3] if len(gene_info) > 3 else 0

            label = f"{node_id}\n({node_type}"
            if node_type == 'hidden':
                label += f", {activation}, b={bias:.2f})"
            elif node_type == 'output':
                label += f", b={bias:.2f})"
            else:
                label += ")"
            G.add_node(node_id, label=label, type=node_type)

        # Add edges
        for (in_node, out_node, _), weight in self.connections.items():
            if in_node in self.genes and out_node in self.genes:
                G.add_edge(in_node, out_node, weight=f"{weight:.2f}")

        # Node colors
        node_colors = {'input': 'lightblue', 'hidden': 'lightgreen', 'output': 'lightcoral'}
        colors = [node_colors[data['type']] for _, data in G.nodes(data=True)]

        # Graphviz layout (hierarchical)
        try:
            pos = nx.nx_agraph.graphviz_layout(G, prog='dot', args='-Grankdir=LR')  # Left-to-right layout
        except:
            print("Error: Asegúrate de tener pygraphviz instalado correctamente.")
            return

        # Draw everything
        nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=700, alpha=0.9)
        nx.draw_networkx_edges(G, pos, arrows=True, width=1.0, alpha=0.6)
        edge_labels = nx.get_edge_attributes(G, 'weight')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=6)
        labels = nx.get_node_attributes(G, 'label')
        nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)

        plt.title(f"Genome ID: {self.genome_id}")
        plt.axis('off')
        plt.tight_layout()
        plt.show()

class Population:
    """
    Clase que representa una población de genomas.

    Attributes
    ----------
    population_size : int
        Indica el tamaño de la población
    population: List
        Lista de genomas que representan la población
    fitness_scores: List
        Lista de los fitness de cada miembro de la población
    best_genome : FeedforwardGenome
        Genoma con el mejor fitness
    innovation_manager: InnovationManager
        Un objeto que gestiona los números de innovación de los genomas.
          
    Methods
    -------
    __init__():
        Inicializa una población de genomas.
    create_initial_genome_population():
        Crea un genoma inicial aleatorio (FeedforwardGenome).
    create_initial_population():
        Crea una población de genomas.
    evaluate_fitness():
        Evalúa el fitness de cada genoma utilizando la función `evaluate_genome`.
    select_genomes():
        Selecciona los mejores genomas para la reproducción a partir del mejor valor de fitness.
    reproduce_and_mutate():
        Crea nuevos genomas mediante cruce y mutación, incluyendo mutación de bias.
    get_best_genome():
        Devuelve el mejor genoma según el fitness más alto.
    get_best_fitness():
        Devuelve el mejor fitness
    __repr__():
        Devuelve una representación en cadena del gen.
    """

    def __init__(self, population_size: int, innovation_manager: 'InnovationManager'):
        """
        Inicializa una población de genomas.
        
        Attributes
        ----------
        population_size (int): Indica el tamaño de la población
        innovation_manager (InnovationManager): Un objeto que gestiona los números de innovación de los genomas.
        """
        self.population_size = population_size
        self.population = []
        self.fitness_scores = [0.0] * population_size
        self.best_genome = None
        self.best_fitness = -float('inf')
        self.innovation_manager = innovation_manager

    def create_initial_genome_population(self, num_inputs: int, num_outputs: int, initial_hidden_nodes: int = 8):
        """
        Crea un genoma inicial aleatorio (FeedforwardGenome).
        
        Attributes
        ----------
        num_inputs (int): El número de entradas del genoma.
        num_outputs (int): El número de salidas del genoma.
        initial_hidden_nodes (int, opcional): El número de nodos ocultos iniciales. Por defecto es 8.
        
        Returns:
        --------
        FeedforwardGenome: Un nuevo genoma inicializado aleatoriamente.
        """
        genome = FeedforwardGenome(genome_id=self.innovation_manager.next_genome_id(),
                                     num_inputs=num_inputs,
                                     num_outputs=num_outputs,
                                     innovation_manager = self.innovation_manager,
                                     initial_hidden_nodes=initial_hidden_nodes)
        self.innovation_manager.increment_genome_id()
        return genome

    def create_initial_population(self, num_inputs: int, num_outputs: int, initial_hidden_nodes: int = 8):
        """
        Crea una población de genomas.
        
        Attributes
        ----------
        num_inputs (int): El número de entradas del genoma.
        num_outputs (int): El número de salidas del genoma.
        initial_hidden_nodes (int, opcional): El número de nodos ocultos iniciales. Por defecto es 8.
        """
        for _ in range(self.population_size):
            self.population.append(self.create_initial_genome_population(num_inputs, num_outputs, initial_hidden_nodes))

    def evaluate_fitness(self, graph_data: List[tuple[torch.Tensor, torch.Tensor]]) -> None:
        """
        Evalúa el fitness de cada genoma utilizando la función `evaluate_genome`.
        
        Attributes
        ----------
        graph_data (List[tuple[torch.Tensor, torch.Tensor]]): Datos de grafos utilizados para evaluar la aptitud.
        """
        self.fitness_scores = []
        for genome in self.population:
            genome.evaluate_genome(graph_data)
            self.fitness_scores.append(genome.fitness)

            if genome.fitness > self.best_fitness:
                self.best_fitness = genome.fitness
                self.best_genome = genome

    def select_genomes(self) -> List['FeedforwardGenome']:
        """
        Selecciona los mejores genomas para la reproducción a partir del mejor valor de fitness.

        Returns:
        --------
        List[FeedforwardGenome]: Los genomas seleccionados con mejor fitness.
        """
        selected_genomes = []
        sorted_population = sorted(self.population, key=lambda genome: genome.fitness, reverse=True)
        num_selected = max(1, self.population_size // 5) # Keep at least one
        selected_genomes.extend(sorted_population[:num_selected])
        return selected_genomes

    def reproduce_and_mutate(self, population_size: int, mutation_rate: float,
                             crossover_function: Callable[['FeedforwardGenome', 'FeedforwardGenome', 'InnovationManager'], 'FeedforwardGenome'],
                             mutate_function: Callable[['FeedforwardGenome', 'InnovationManager', float], 'FeedforwardGenome'],
                             bias_mutation_rate: float = 0.3, # Add a bias mutation rate
                             bias_mutation_power: float = 0.3) -> None:
        """
        Crea nuevos genomas mediante cruce y mutación, incluyendo mutación de bias.
        
        Attributes
        ----------
        population_size (int): El tamaño deseado de la población después de la reproducción.
        mutation_rate (float): La tasa de mutación que se aplicará a los genomas.
        crossover_function (Callable): Función que toma dos genomas y devuelve un genoma cruzado.
        mutate_function (Callable): Función que aplica mutaciones a un genoma.
        bias_mutation_rate (float, opcional): La tasa de mutación de bias. Por defecto es 0.3.
        bias_mutation_power (float, opcional): El poder de la mutación de bias. Por defecto es 0.3.
        """
        selected_genomes = self.select_genomes()
        new_population = selected_genomes[:]
        while len(new_population) < population_size:
            parent1 = random.choice(selected_genomes)
            parent2 = random.choice(selected_genomes)
            child = crossover_function(parent1, parent2, self.innovation_manager)
            child = mutate_function(child, self.innovation_manager, mutation_rate)
            child.mutate_biases(bias_mutation_rate, bias_mutation_power) # Mutate biases
            new_population.append(child)
        self.population = new_population

    def get_best_genome(self) -> 'FeedforwardGenome':
        """
        Devuelve el mejor genoma según el fitness más alto.

        Returns:
        --------
        FeedforwardGenome: El genoma con el mejor fitness.
        """
        return self.best_genome

    def get_best_fitness(self) -> float:
        """
        Devuelve el mejor fitness

        Returns
        -------
        float: El mejor fitness.
        """
        return self.best_fitness
 
class InnovationManager:
    """
    Clase para gestionar los números de innovación y los IDs de los genomas.
    Esta clase es responsable de la asignación única de números de innovación para genes y conexiones,
    así como de la asignación de IDs únicos para los genomas.

    Attributes
    ----------
    innovations : dict
        Diccionario para almacenar las innovaciones existentes.
    next_innovation_number: int
        Contador para el próximo número de innovación disponible.
    fitness_scores: List
        Counter for the next available genome ID
          
    Methods
    -------
    __init__():
        Inicializa el InnovationManager, comenzando con un contador de innovaciones y un contador de ID de genoma.
    get_innovation_number():
        Obtiene el número de innovación de una innovación existente.
    create_innovation():
        Crea y registra una nueva innovación, o reutiliza un número existente.
    next_genome_id():
        Devuelve el número de id disponible
    increment_genome_id():
        Actualiza el id disponible.
    """
    def __init__(self):
        """
        Inicializa el InnovationManager, comenzando con un contador de innovaciones y un contador de ID de genoma.
        """
        self.innovations = {}  # Diccionario para almacenar las innovaciones existentes.
        self.next_innovation_number = 1  # Contador para el próximo número de innovación disponible.
        self.next_genome_id_counter = 0 # Contador para el id del próximo genoma

    def get_innovation_number(self, innovation_type: str, gene_in_id: int, gene_out_id: int) -> int or None:
        """
        Obtiene el número de innovación de una innovación existente.

        Attributes
        ----------
        innovation_type (str): El tipo de innovación (por ejemplo, 'connection' o 'node').
        gene_in_id (int): El ID del gen que recibe la conexión.
        gene_out_id (int): El ID del gen que emite la conexión.

        Returns
        -------
        int o None: El número de innovación existente si la innovación está registrada, 
                    o None si la innovación no se ha registrado previamente.
        """
        return self.innovations.get((innovation_type, gene_in_id, gene_out_id))

    def create_innovation(self, innovation_type: str, gene_in_id: int, gene_out_id: int, innovation_number: int = None) -> int:
        """
        Crea y registra una nueva innovación, o reutiliza un número existente.

        Attributes
        ----------
        innovation_type (str): El tipo de innovación (por ejemplo, 'connection' o 'node').
        gene_in_id (int): El ID del gen que recibe la conexión.
        gene_out_id (int): El ID del gen que emite la conexión.
        innovation_number (int, opcional): El número de innovación a utilizar. Si no se proporciona, se genera uno automáticamente.

        Returns
        -------
        int: El número de innovación que se ha registrado o reutilizado.
        """
        if innovation_number is None:
            innovation_number = self.next_innovation_number
            self.next_innovation_number += 1
        self.innovations[(innovation_type, gene_in_id, gene_out_id)] = innovation_number
        return innovation_number

    def next_genome_id(self) -> int:
        """
        Devuelve el número de id disponible
        
        Returns
        -------
        int: El id del genoma disponible
        """
        genome_id = self.next_genome_id_counter
        self.next_genome_id_counter += 1
        return genome_id

    def increment_genome_id(self):
        """
        Actualiza el id disponible.
        """
        self.next_genome_id_counter += 1

class Species:
    """
    Clase para agrupar genomas similares.
    
    Attributes
    ----------
    representative_genome (FeedforwardGenome): El genoma representativo de la especie
    members (List): Lista de los miembros de la especie
    adjusted_fitnesses (dict): Diccionario que por cada genoma, almacena su fitness ajustado. 
    best_fitness (float): Almacena el fitness del mejor genoma
    last_improved (int): Generación en la que mejoró el fitness por última vez
    historical_best_fitness (float): Almacena el mejor fitness que se haya registrado para la especie
    
    Methods
    -------
    __init__():
        Inicializa una especie con un genoma representativo.
    add_member():
        Agrega un genoma a la especie.
    is_compatible():
        Verifica si un genoma es compatible con la especie.
    calculate_compatibility_distance():
        Calcula la distancia de compatibilidad entre un genoma y el representativo.
    adjust_fitnesses():
        Ajusta los fitness de los genomas dentro de la especie.
    get_adjusted_fitness():
        Obtiene el fitness ajustado de un genoma.
    clear():
        Limpia la lista de miembros de la especie, manteniendo solo al representante.
    update_best_fitness():
        Actualizar el mejor fitness de la especie, la generación en la que mejoró. 
    
    """

    def __init__(self, representative_genome: 'FeedforwardGenome'):
        """
        Inicializa una especie con un genoma representativo.

        Attributes
        ----------
        representative_genome : Genome
            El genoma que representa a esta especie.  Los nuevos genomas se comparan con este genoma
            para determinar si pertenecen a esta especie.
        """
        self.representative_genome = representative_genome
        self.members = [representative_genome]  # Inicialmente, solo el representante es miembro
        self.adjusted_fitnesses = {}  # Almacena el fitness ajustado de cada miembro
        self.best_fitness = representative_genome.fitness if hasattr(representative_genome, 'fitness') else -float('inf')
        self.last_improved = 0  # Generación en la que mejoró el fitness por última vez
        self.historical_best_fitness = self.best_fitness

    def add_member(self, genome: 'FeedforwardGenome'):
        """
        Agrega un genoma a la especie.

        Attributes
        ----------
        genome : Genome
            El genoma a agregar a esta especie.
        """
        self.members.append(genome)

    def is_compatible(self, genome: 'FeedforwardGenome', compatibility_threshold: float) -> bool:
        """
        Verifica si un genoma es compatible con la especie.

        La compatibilidad se determina comparando la distancia genómica
        entre el genoma dado y el genoma representativo de la especie.

        Attributes
        ----------
        genome : Genome
            El genoma a comparar con el representante de la especie.
        compatibility_threshold : float
            El umbral de distancia de compatibilidad.  Si la distancia
            es menor o igual a este umbral, el genoma se considera compatible.

        Returns
        -------
        bool
            True si el genoma es compatible, False de lo contrario.
        """
        distance = self.calculate_compatibility_distance(genome)
        return distance <= compatibility_threshold

    def calculate_compatibility_distance(self, genome: 'FeedforwardGenome', c1: float = 1.0, c2: float = 1.0, c3: float = 1.0) -> float:
        """
        Calcula la distancia de compatibilidad entre un genoma y el representativo.

        Esta distancia se utiliza para determinar si dos genomas son lo suficientemente
        similares como para estar en la misma especie.  Utiliza la distancia
        genómica definida por NEAT, que considera:
        - Exceso de genes: Genes presentes en un genoma pero no en el otro.
        - Genes disjuntos: Genes no coincidentes que no son excesivos.
        - Diferencia de peso: Diferencia absoluta en los pesos de los genes coincidentes.

        Attributes
        ----------
        genome : Genome
            El genoma a comparar con el representante de la especie.
        c1 : float, opcional
            Coeficiente para el término de exceso de genes. Por defecto es 1.0.
        c2 : float, opcional
            Coeficiente para el término de genes disjuntos. Por defecto es 1.0.
        c3 : float, opcional
            Coeficiente para el término de diferencia de peso. Por defecto es 1.0.

        Returns
        -------
        float
            La distancia de compatibilidad.
        """
        excess = 0
        disjoint = 0
        weight_diff = 0
        matching = 0

        # Obtener los genes y conexiones de ambos genomas
        genes1 = self.representative_genome.genes
        genes2 = genome.genes
        connections1 = self.representative_genome.connections
        connections2 = genome.connections

        # Obtener los números de innovación de los genes
        innovation_numbers1_genes = {gene[2] for gene in genes1.values() if len(gene) > 2 and gene[2] is not None}
        innovation_numbers2_genes = {gene[2] for gene in genes2.values() if len(gene) > 2 and gene[2] is not None}

        # Calcular exceso y disjoint para genes
        max_innovation1_genes = max(innovation_numbers1_genes) if innovation_numbers1_genes else 0
        max_innovation2_genes = max(innovation_numbers2_genes) if innovation_numbers2_genes else 0
        max_innovation_genes = max(max_innovation1_genes, max_innovation2_genes)

        for innovation_number in range(1, max_innovation_genes + 1):
            in1 = innovation_number in innovation_numbers1_genes
            in2 = innovation_number in innovation_numbers2_genes

            if in1 and in2:
                continue
            elif in1 or in2:
                if innovation_number > min(max_innovation1_genes, max_innovation2_genes):
                    excess += 1
                else:
                    disjoint += 1

        # Calcular exceso, disjoint y diferencia de peso para conexiones
        innovation_numbers1_connections = {conn[2] for conn in connections1}
        innovation_numbers2_connections = {conn[2] for conn in connections2}

        max_innovation1_conn = max(innovation_numbers1_connections) if innovation_numbers1_connections else 0
        max_innovation2_conn = max(innovation_numbers2_connections) if innovation_numbers2_connections else 0
        max_innovation_conn = max(max_innovation1_conn, max_innovation2_conn)

        total_weight_diff = 0
        matching_connections = 0

        for innovation_number in range(1, max_innovation_conn + 1):
            conn1_list = [conn for conn in connections1 if conn[2] == innovation_number]
            conn2_list = [conn for conn in connections2 if conn[2] == innovation_number]

            if conn1_list and conn2_list:
                conn1_key = conn1_list[0]
                conn2_key = conn2_list[0]
                matching_connections += 1
                total_weight_diff += abs(connections1[conn1_key] - connections2[conn2_key])
            elif conn1_list or conn2_list:
                if innovation_number > min(max_innovation1_conn, max_innovation2_conn):
                    excess += 1
                else:
                    disjoint += 1

        # Calcular distancia de compatibilidad
        N = max(len(genes1), len(genes2), len(connections1), len(connections2))
        if N == 0:
            N = 1  # Para evitar la división por cero
        distance = (c1 * excess / N) + (c2 * disjoint / N) + (c3 * weight_diff / N)

        return distance

    def adjust_fitnesses(self):
        """
        Ajusta los fitness de los genomas dentro de la especie.

        Implementa la compartición de fitness: el fitness de cada genoma
        se divide por el número de miembros en su especie. Esto reduce
        la ventaja de las especies grandes y previene el estancamiento genético.
        """
        species_size = len(self.members)
        self.adjusted_fitnesses = {}  # Reinicia los fitness ajustados
        for genome in self.members:
            adjusted_fitness = genome.fitness / species_size  # Compartición de fitness
            self.adjusted_fitnesses[genome] = adjusted_fitness

    def get_adjusted_fitness(self, genome: 'FeedforwardGenome') -> float:
        """
        Obtiene el fitness ajustado de un genoma.

        Si el genoma no está en la especie, devuelve su fitness sin ajustar.

        Attributes
        ----------
        genome : Genome
            El genoma del cual se quiere obtener el fitness ajustado.

        Returns
        -------
        float
            El fitness ajustado del genoma, o el fitness sin ajustar si el genoma no está en la especie.
        """
        return self.adjusted_fitnesses.get(genome, genome.fitness)

    def clear(self):
        """
        Limpia la lista de miembros de la especie, manteniendo solo al representante.
        """
        # Keep the best member as the representative for the next generation
        if self.members:
            self.members.sort(key=lambda genome: genome.fitness, reverse=True)
            self.representative_genome = self.members[0]
            self.members = [self.representative_genome]

    def update_best_fitness(self, fitness: float):
        """
        Actualizar el mejor fitness de la especie, la generación en la que mejoró. 
        
        Revisa si se debe mejorar el histórico
        """
        global current_generation  # Assuming current_generation is in the global scope
        if fitness > self.best_fitness:
            self.best_fitness = fitness
            self.historical_best_fitness = max(self.historical_best_fitness, fitness)
            self.last_improved = current_generation

class StagnationManager:
    def __init__(self, max_stagnation=15, elitism=2):
        self.max_stagnation = max_stagnation
        self.elitism = elitism
        self.species_last_improved = {}
        self.sorted_species = SortedList(key  = lambda spec: spec.best_fitness)

    def update(self, species_list: List['Species'], generation: int) -> Dict['Species', bool]:
        stagnation_status = {}
        
        for spec in species_list:
            if spec in self.sorted_species:
                self.sorted_species.remove(spec)
                self.sorted_species.add(spec)
            else:
                self.sorted_species.add(spec)

        results = []
        for spec in self.sorted_species:
            # Initialize last improved generation if the species is new
            if spec not in self.species_last_improved:
                self.species_last_improved[spec] = generation
                self.update_historical_best_fitness(spec, spec.best_fitness)
                stagnation_status[spec] = False
            # Check for improvement
            elif spec.best_fitness > self.get_historical_best_fitness(spec):
                self.species_last_improved[spec] = generation
                self.update_historical_best_fitness(spec, spec.best_fitness)
                stagnation_status[spec] = False
            # Check for stagnation
            elif (generation - self.species_last_improved[spec]) >= self.max_stagnation:
                stagnation_status[spec] = True
            else:
                stagnation_status[spec] = False
            results.append((spec, stagnation_status[spec]))

        # Mark the top 'elitism' species as not stagnant
        results.sort(key=lambda x: max(g.fitness for g in x[0].members) if x[0].members else -float('inf'), reverse=True)
        for i in range(min(self.elitism, len(results))):
            results[i] = (results[i][0], False)
            stagnation_status[results[i][0]] = False

        return stagnation_status

    def get_historical_best_fitness(self, species: 'Species') -> float:
        return getattr(species, 'historical_best_fitness', -float('inf'))

    def update_historical_best_fitness(self, species: 'Species', fitness: float):
        setattr(species, 'historical_best_fitness', max(self.get_historical_best_fitness(species), fitness))

def evaluate_genome(genome: FeedforwardGenome, graph_features: torch.Tensor, target_average_path: torch.Tensor) -> float:
    """
    Evaluates the fitness of a FeedforwardGenome.

        Attributes
        ----------
        genome (FeedforwardGenome): The genome to evaluate.
        graph_features (torch.Tensor): The input features extracted from the graphs.
                                       This should have a shape compatible with the input size of your Net.
        target_average_path (torch.Tensor): The target average node path for the corresponding graphs.
                                            This should have a shape compatible with the output size of your Net (which is 1).

        Returns
        -------
        float: The fitness score of the genome. Higher is generally better.
    """
    # 1. Create the PyTorch network from the genome
    num_inputs = graph_features.shape[1]  # Assuming graph_features shape is (batch_size, num_features)
    net = genome.create_pytorch_network(num_inputs=num_inputs)
    net.eval()  # Set the network to evaluation mode

    # 2. Ensure graph_features has a batch dimension (unsqueeze at dimension 0 if necessary)
    if len(graph_features.shape) == 1:
        graph_features = graph_features.unsqueeze(0)  # Now it's (1, num_features)

    # 3. Perform forward pass
    with torch.no_grad():
        output = net(graph_features)

    # 4. Ensure target has the batch dimension
    if len(target_average_path.shape) == 1:
        target_average_path = target_average_path.unsqueeze(0)  # Ensure target also has batch dimension
    
    # 5. Calculate fitness based on the output and target
    criterion = nn.MSELoss()
    loss = criterion(output, target_average_path)
    fitness = -loss.item()  # Negative loss as fitness (lower loss means better fitness)

    return fitness

def crossover(parent1: FeedforwardGenome, parent2: FeedforwardGenome, innovation_manager: InnovationManager) -> FeedforwardGenome:
    """
    Función que realiza el cruce entre dos padres genoma para producir un hijo genoma
    
    Attributes:
    -----------
    parent1 (FeedforwardGenome): genoma que actúa como el primer padre
    parent2 (FeedforwardGenome): genoma que actúa como el segundo padre
    innovation_manager (InnovationManager): Un objeto que gestiona los números de innovación de los genomas.
    
    Returns:
    --------
    Devuelve un genoma resultante del cruce entre sus padres
    """

    fittest_parent = parent1 if parent1.fitness > parent2.fitness else parent2
    child = FeedforwardGenome(genome_id=innovation_manager.next_genome_id(),
                                num_inputs=sum(1 for gene_info in parent1.genes.values() if gene_info[0] == 'input'),
                                num_outputs=sum(1 for gene_info in parent1.genes.values() if gene_info[0] == 'output'),
                                innovation_manager = innovation_manager)
    innovation_manager.increment_genome_id()

    genes1 = parent1.genes
    genes2 = parent2.genes
    connections1 = parent1.connections
    connections2 = parent2.connections

    child.genes = {}
    # Crossover genes based on innovation number
    all_gene_innovations = set(gene_info[2] for gene_info in genes1.values()) | set(gene_info[2] for gene_info in genes2.values())
    for innovation in sorted(list(all_gene_innovations)):
        gene1_item = next(((node_id, gene_info) for node_id, gene_info in genes1.items() if gene_info[2] == innovation), None)
        gene2_item = next(((node_id, gene_info) for node_id, gene_info in genes2.items() if gene_info[2] == innovation), None)

        if gene1_item and gene2_item:
            node_id1, gene1 = gene1_item
            node_id2, gene2 = gene2_item
            if random.random() < 0.5:
                child.genes[node_id1] = (gene1[0], gene1[1], gene1[2], gene1[3] if len(gene1) > 3 else 0)
            else:
                child.genes[node_id2] = (gene2[0], gene2[1], gene2[2], gene2[3] if len(gene2) > 3 else 0)
        elif gene1_item and fittest_parent == parent1:
            node_id, gene1 = gene1_item
            child.genes[node_id] = gene1
        elif gene2_item and fittest_parent == parent2:
            node_id, gene2 = gene2_item
            child.genes[node_id] = gene2

    child.connections = {}
    # Crossover connections based on innovation number
    all_connection_innovations = set(innov for _, _, innov in connections1.keys()) | set(innov for _, _, innov in connections2.keys())
    for innovation in sorted(list(all_connection_innovations)):
        conn1 = next((((in_node, out_node, innov), weight) for (in_node, out_node, innov), weight in connections1.items() if innov == innovation), None)
        conn2 = next((((in_node, out_node, innov), weight) for (in_node, out_node, innov), weight in connections2.items() if innov == innovation), None)

        if conn1 and conn2:
            chosen_conn, weight = conn1 if random.random() < 0.5 else conn2
            child.connections[(chosen_conn[0], chosen_conn[1], innovation)] = weight
        elif conn1 and fittest_parent == parent1:
            child.connections[conn1[0]] = conn1[1]
        elif conn2 and fittest_parent == parent2:
            child.connections[conn2[0]] = conn2[1]

    # Ensure child's next_node_id is consistent
    if child.genes:
        child.next_node_id = max(child.genes.keys()) + 1
    else:
        child.next_node_id = 0

    return child
    
def mutate(genome: FeedforwardGenome, innovation_manager: InnovationManager,
           mutation_rate: float = 0.3, weight_mutation_rate: float = 0.2,
           add_node_rate: float = 0.3, add_connection_rate: float = 0.3,
           eliminate_node_rate: float = 0.2, eliminate_connection_rate: float = 0.2) -> FeedforwardGenome:
    """
    Función que controla las mutaciones del genoma en todos los niveles
    
    Restricciones:
    
    1. no se pueden eliminar los nodos de entrada ni el nodo de salida
    
    2. Los nodos de entrada y el nodo de salida no pueden quedar aislados
    
    3. Los nodos ocultos deben ser siempre puente de información, deben siempre tener al menos una entrada y al menos una salida
    
    Attributes:
    -----------
    genome (FeedforwardGenome): genoma que se quiere mutar
    innovation_manager (InnovationManager): Un objeto que gestiona los números de innovación de los genomas.
    mutation_rate (float): valor con el cual se controla con qué frecuencia se realiza una mutación
    weight_mutation_rate (float): valor con el cual se controla con qué frecuencia se muta el peso de una conexión
    add_node_rate (float): valor con el cual se controla con qué frecuencia se agrega un nodo al genoma
    add_connection_rate (float): valor con el cual se controla con qué frecuencia se agrega una conexión
    eliminate_node_rate (float): valor con el cual se controla con qué frecuencia se elimina un nodo
    eliminate_connection_rate (float): valor con el cual se controla con qué frecuencia se elimina una conexión   
    """

    # Mutate weights
    if random.random() < weight_mutation_rate and genome.connections:
        genome.mutate_weights(mutation_rate=0.5, weight_mutation_power=0.2)

    # Mutate biases
    if random.random() < mutation_rate: # Using general mutation rate for bias
        genome.mutate_biases(mutation_rate=0.5, bias_mutation_power=0.2)

    # Add new node
    if random.random() < add_node_rate and genome.connections:
        possible_in_nodes = [node_id for node_id in genome.genes if genome.genes[node_id][0] != 'output']
        possible_out_nodes = [node_id for node_id in genome.genes if genome.genes[node_id][0] != 'input']
        genome.mutate_add_node(possible_in_nodes, possible_out_nodes, innovation_manager)

    # Add new connection
    if random.random() < add_connection_rate and len(genome.genes) >= 2:
        possible_in_nodes = [node_id for node_id in genome.genes if genome.genes[node_id][0] != 'output']
        possible_out_nodes = [node_id for node_id in genome.genes if genome.genes[node_id][0] != 'input']
        genome.mutate_add_connection(possible_in_nodes, possible_out_nodes, innovation_manager)

    # Eliminate node
    if random.random() < eliminate_node_rate and genome.get_num_hidden_nodes() > 0: # Need to add this method to Genome
        genome.mutate_eliminate_node()

    # Eliminate connection
    if random.random() < eliminate_connection_rate and genome.connections:
        genome.mutate_eliminate_connection()

    return genome

def log_mse_loss(predictions, targets):
    """Calculates MSE on the log-transformed values."""
    log_predictions = torch.log(torch.abs(predictions) + 1e-6) # Add epsilon to avoid log(0)
    log_targets = torch.log(torch.abs(targets) + 1e-6)
    criterion = nn.MSELoss()
    return criterion(log_predictions, log_targets)

def percentage_mse_loss(predictions, targets):
    """Calculates the Mean Squared Percentage Error (MSPE)."""
    epsilon = 1e-6
    percentage_errors = ((predictions - targets) / (targets + epsilon)) * 100
    return torch.mean(percentage_errors**2)

def percentage_mae_loss(predictions, targets):
    """Calculates the Mean Absolute Percentage Error (MAPE)."""
    epsilon = 1e-6
    absolute_percentage_errors = torch.abs((predictions - targets) / (targets + epsilon)) * 100
    return torch.mean(absolute_percentage_errors)


#************************************** Definición de funciones para GNN *******************************************#

