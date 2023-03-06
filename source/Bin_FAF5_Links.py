# Import needed modules
from qgis.core import *
import qgis.utils
from qgis.PyQt import QtGui
import os
from console.console import _console
import sys
import os.path

def main():

    # Get the path to top level of the git directory so we can use relative paths
    source_dir = os.path.dirname(_console.console.tabEditorWidget.currentWidget().path)
    if source_dir.endswith('/source'):
        top_dir = source_dir[:-7]
    elif source_dir.endswith('/source/'):
        top_dir = source_dir[:-8]
    else:
        print("ERROR: Expect current directory to end with 'source'. Cannot use relative directories as-is. Exiting...")
        sys.exitfunc()
        
    def make_joined_shapefile():

        ##################################### Load and process FAF5 netowrk links ######################################
        # Load in the FAF5 network links shapefile
        links = QgsVectorLayer(f'{top_dir}/data/FAF5_network_links/Freight_Analysis_Framework_(FAF5)_Network_Links.shp', 'FAF5 Links', 'ogr')

        # Confirm that the netowrk links got loaded in correctly
        if not links.isValid():
          print('Layer failed to load!')
        
        ################################################################################################################

        ################################## Load and process FAF5 highway assignments ###################################
        # Read in the total highway trucking flows by commodity for 2022
        uri = f'{top_dir}/data/FAF5_Highway_Assignment_Results/FAF5_2022_Highway_Assignment_Results/CSV Format/FAF5 Total Truck Flows by Commodity_2022.csv'
        assignments = QgsVectorLayer(uri, 'FAF5 Assignments', 'ogr')

        # Skim the assignments down to what we want to work with, and make sure the variable types are correct (by default QGIS reads in CSV data as strings, even if they're actually numbers)
        # Note:
        proc = processing.run("native:refactorfields", {'INPUT':uri,'FIELDS_MAPPING':[{'expression': '"ID"','length': 0,'name': 'ID','precision': 0,'sub_type': 0,'type': 2,'type_name': 'integer'},{'expression': '"TOT Tons_22 All"','length': 0,'name': 'TOT Tons_22 All','precision': 0,'sub_type': 0,'type': 6,'type_name': 'double precision'}],'OUTPUT':'TEMPORARY_OUTPUT'})
        assignments = proc['OUTPUT']

        # Confirm that the highway assignments got loaded in correctly
        if not assignments.isValid():
          print('Layer failed to load!')

        ################################################################################################################

        ################## Join the FAF5 assignments to the highway networks via the highway link IDs ##################
        #assignments = iface.activeLayer()

        # Initialize a vector layer join info object to specify how the join will be performed
        info = QgsVectorLayerJoinInfo()

        # The common field to be used for joining is the network link ID (called 'ID' in both the assignments and links layers)
        info.setJoinFieldName('ID')
        info.setTargetFieldName('ID')
        info.setJoinLayer(assignments)

        # Specify that the joined layer will be stored in memory for ready access
        info.setUsingMemoryCache(True)

        # Apply the join to the network links layer
        links.addJoin(info)
        _writer = QgsVectorFileWriter.writeAsVectorFormat(links, f'{top_dir}/data_out/network_links_all.shp', 'utf-8', driverName='ESRI Shapefile')
        ################################################################################################################
        
    def get_bin_edges():
        links = QgsVectorLayer(f'{top_dir}/data_out/network_links_all.shp', 'FAF5 Links', 'ogr')
        # Confirm that the netowrk links got loaded in correctly
        if not links.isValid():
          print('Layer failed to load!')

        ######################### Style the network links to have width proportional to tonnage ########################
        # Target field is by default the total tons transported as weighting factor for network link widths
        myTargetField = 'Refactored'

        # Specify the range of possible weighting factors as the max and min range of the target field
        ramp_max = links.maximumValue(links.fields().indexFromName(myTargetField))
        ramp_min = links.minimumValue(links.fields().indexFromName(myTargetField))

        # Classify the tonnages into 5 bins
        ramp_num_steps = 5

        # Initialize a graduated renderer object specify how the network link symbol properties will vary according to the numerical target field
        renderer = QgsGraduatedSymbolRenderer(myTargetField)
        renderer.setClassAttribute(myTargetField)

        # Specify the network link symbol to be a black line in all cases
        symbol = QgsSymbol.defaultSymbol(links.geometryType())
        symbol.setColor(QtGui.QColor('#000000'))
        renderer.setSourceSymbol(symbol)

        # Specify the binning method (jenks), number of bins, and range of line widths for the graduated renderer
        renderer.setClassificationMethod(QgsClassificationJenks())
        renderer.updateClasses(links, ramp_num_steps)
        renderer.setSymbolSizes(0.1, 3)
        #renderer.updateColorRamp()

        # Apply the graduated symbol renderer defined above to the network links
        links.setRenderer(renderer)
        
        # Get the ranges
        ranges = renderer.ranges()
        bin_edges = []
        bin_edges.append(ranges[0].lowerValue())
        for this_range in ranges:
            bin_edges.append(this_range.upperValue())
        return links, bin_edges
        ################################################################################################################
    
    def make_binned_shapefiles(links, bin_edges):
        ############################### Save a separate set of network links for each bin ##############################
        import numpy as np
        for i in np.arange(len(bin_edges)-1):
           links.setSubsetString(f'"Refactored" >= {bin_edges[i]} AND "Refactored" <= {bin_edges[i+1]}')
           QgsVectorFileWriter.writeAsVectorFormat(links, f'{top_dir}/data_out/network_links_{bin_edges[i]}_{bin_edges[i+1]}.shp', 'utf-8', driverName='ESRI Shapefile')
        ################################################################################################################
        
    if not os.path.isfile(f'{top_dir}/data_out/network_links_all.shp'):
        make_joined_shapefile()
        
    links, bin_edges = get_bin_edges()
    print(bin_edges)
    make_binned_shapefiles(links, bin_edges)
    

main()

