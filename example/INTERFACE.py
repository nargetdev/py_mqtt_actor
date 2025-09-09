#!/usr/bin/env python3
"""
Simple Pydantic test object specification
"""

from pydantic import BaseModel


class SimpleObject(BaseModel):
    """An object with an int and a bool"""
    
    int_value: int
    bool_value: bool



class TestObject(BaseModel):
    """A simple test object with basic data types"""
    
    string_element: str
    priority: float
    simple_object: SimpleObject

class ResponseObject(BaseModel):
    """Response object for the TestObject actor"""
    status: int
    output_file: str