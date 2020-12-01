# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 15:32:24 2020

@author: b.mayer

This validation preprocessor extends submitted update data silently if possible.
So that partial updates or redundant field  definitions like pint's dimensionality do not have to be submitted everytime. 
"""

import flask

from ...logic import objects, datatypes, errors, units
from .utils import units_are_valid, get_dimensionality_for_units

def _validation_preprocessor_object(instance: dict, schema: dict, object_id: int) -> None:
    """
    If the given object is the root object to be updated 
    (not a data type "object" reference to another object)
    then this function extends the data in the instance dictionary 
    in case there are any schema properties missing with the data 
    from the objects current version. This allows for partial updates 
    via the API while keeping the rest of the data untouched.
    
    This function can be toggled on via the configuration parameter SAMPLEDB_ALLOW_PARTIAL_OBJECT_UPDATES

    :param instance: the sample object
    :param schema: the valid sampledb object schema
    """
    if flask.current_app.config['ALLOW_PARTIAL_OBJECT_UPDATES'] == False:
        return
    
    if not isinstance(instance, dict) or object_id == None:
        return
        
    current_object = objects.get_object(object_id)
    if current_object is None:
        return 
        
    for key in current_object.data:
        if key not in instance:
            instance[key] = current_object.data[key]

    
def _validation_preprocessor_quantity(instance: dict, schema: dict) -> None:
    """
    Extends the json to update a quantity object by the unit from the schema, 
    the dimensionality and either the magnitude or the magnitute_in_base_units parameter
    
    :param instance: the sample object
    :param schema: the valid sampledb object schema
    """
    
    if not isinstance(instance, dict):
        return instance
    if '_type' not in instance:
        return instance #maybe set to schema type?
    if 'units' not in instance:
        instance['units'] = schema['units']
        
    magnitude_datatype = None
    magnitude_base_datatype = None
    if 'magnitude' in instance:
        magnitude_datatype = datatypes.Quantity(instance['magnitude'], units=instance['units'], already_in_base_units=False)
    if 'magnitude_in_base_units' in instance:
        magnitude_base_datatype = datatypes.Quantity(instance['magnitude_in_base_units'], units=instance['units'], already_in_base_units=True)
    
    if magnitude_datatype is not None and magnitude_base_datatype is not None and magnitude_datatype != magnitude_base_datatype:
        raise errors.ValidationError('magnitude and magnitude_in_base_units do not match, either set only one or make sure both match', None)
    elif magnitude_datatype is None:
        magnitude_datatype = magnitude_base_datatype
        
    instance.update(magnitude_datatype.to_json())
        
