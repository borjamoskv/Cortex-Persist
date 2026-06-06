# MejoraloScanRequest

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Project** | **string** |  | 
**Path** | **string** | Ruta al directorio del proyecto | 
**Deep** | Pointer to **bool** | Activa dimensión Psi + análisis profundo | [optional] [default to false]

## Methods

### NewMejoraloScanRequest

`func NewMejoraloScanRequest(project string, path string, ) *MejoraloScanRequest`

NewMejoraloScanRequest instantiates a new MejoraloScanRequest object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewMejoraloScanRequestWithDefaults

`func NewMejoraloScanRequestWithDefaults() *MejoraloScanRequest`

NewMejoraloScanRequestWithDefaults instantiates a new MejoraloScanRequest object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetProject

`func (o *MejoraloScanRequest) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *MejoraloScanRequest) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *MejoraloScanRequest) SetProject(v string)`

SetProject sets Project field to given value.


### GetPath

`func (o *MejoraloScanRequest) GetPath() string`

GetPath returns the Path field if non-nil, zero value otherwise.

### GetPathOk

`func (o *MejoraloScanRequest) GetPathOk() (*string, bool)`

GetPathOk returns a tuple with the Path field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPath

`func (o *MejoraloScanRequest) SetPath(v string)`

SetPath sets Path field to given value.


### GetDeep

`func (o *MejoraloScanRequest) GetDeep() bool`

GetDeep returns the Deep field if non-nil, zero value otherwise.

### GetDeepOk

`func (o *MejoraloScanRequest) GetDeepOk() (*bool, bool)`

GetDeepOk returns a tuple with the Deep field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeep

`func (o *MejoraloScanRequest) SetDeep(v bool)`

SetDeep sets Deep field to given value.

### HasDeep

`func (o *MejoraloScanRequest) HasDeep() bool`

HasDeep returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


