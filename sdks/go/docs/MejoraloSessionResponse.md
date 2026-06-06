# MejoraloSessionResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**FactId** | **int32** |  | 
**Project** | **string** |  | 
**Delta** | **int32** |  | 
**Status** | Pointer to **string** |  | [optional] [default to "recorded"]

## Methods

### NewMejoraloSessionResponse

`func NewMejoraloSessionResponse(factId int32, project string, delta int32, ) *MejoraloSessionResponse`

NewMejoraloSessionResponse instantiates a new MejoraloSessionResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewMejoraloSessionResponseWithDefaults

`func NewMejoraloSessionResponseWithDefaults() *MejoraloSessionResponse`

NewMejoraloSessionResponseWithDefaults instantiates a new MejoraloSessionResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetFactId

`func (o *MejoraloSessionResponse) GetFactId() int32`

GetFactId returns the FactId field if non-nil, zero value otherwise.

### GetFactIdOk

`func (o *MejoraloSessionResponse) GetFactIdOk() (*int32, bool)`

GetFactIdOk returns a tuple with the FactId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFactId

`func (o *MejoraloSessionResponse) SetFactId(v int32)`

SetFactId sets FactId field to given value.


### GetProject

`func (o *MejoraloSessionResponse) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *MejoraloSessionResponse) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *MejoraloSessionResponse) SetProject(v string)`

SetProject sets Project field to given value.


### GetDelta

`func (o *MejoraloSessionResponse) GetDelta() int32`

GetDelta returns the Delta field if non-nil, zero value otherwise.

### GetDeltaOk

`func (o *MejoraloSessionResponse) GetDeltaOk() (*int32, bool)`

GetDeltaOk returns a tuple with the Delta field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDelta

`func (o *MejoraloSessionResponse) SetDelta(v int32)`

SetDelta sets Delta field to given value.


### GetStatus

`func (o *MejoraloSessionResponse) GetStatus() string`

GetStatus returns the Status field if non-nil, zero value otherwise.

### GetStatusOk

`func (o *MejoraloSessionResponse) GetStatusOk() (*string, bool)`

GetStatusOk returns a tuple with the Status field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStatus

`func (o *MejoraloSessionResponse) SetStatus(v string)`

SetStatus sets Status field to given value.

### HasStatus

`func (o *MejoraloSessionResponse) HasStatus() bool`

HasStatus returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


