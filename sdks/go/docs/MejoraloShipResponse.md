# MejoraloShipResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Project** | **string** |  | 
**Ready** | **bool** |  | 
**Seals** | [**[]ShipSealModel**](ShipSealModel.md) |  | 
**Passed** | **int32** |  | 
**Total** | Pointer to **int32** |  | [optional] [default to 7]

## Methods

### NewMejoraloShipResponse

`func NewMejoraloShipResponse(project string, ready bool, seals []ShipSealModel, passed int32, ) *MejoraloShipResponse`

NewMejoraloShipResponse instantiates a new MejoraloShipResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewMejoraloShipResponseWithDefaults

`func NewMejoraloShipResponseWithDefaults() *MejoraloShipResponse`

NewMejoraloShipResponseWithDefaults instantiates a new MejoraloShipResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetProject

`func (o *MejoraloShipResponse) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *MejoraloShipResponse) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *MejoraloShipResponse) SetProject(v string)`

SetProject sets Project field to given value.


### GetReady

`func (o *MejoraloShipResponse) GetReady() bool`

GetReady returns the Ready field if non-nil, zero value otherwise.

### GetReadyOk

`func (o *MejoraloShipResponse) GetReadyOk() (*bool, bool)`

GetReadyOk returns a tuple with the Ready field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetReady

`func (o *MejoraloShipResponse) SetReady(v bool)`

SetReady sets Ready field to given value.


### GetSeals

`func (o *MejoraloShipResponse) GetSeals() []ShipSealModel`

GetSeals returns the Seals field if non-nil, zero value otherwise.

### GetSealsOk

`func (o *MejoraloShipResponse) GetSealsOk() (*[]ShipSealModel, bool)`

GetSealsOk returns a tuple with the Seals field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSeals

`func (o *MejoraloShipResponse) SetSeals(v []ShipSealModel)`

SetSeals sets Seals field to given value.


### GetPassed

`func (o *MejoraloShipResponse) GetPassed() int32`

GetPassed returns the Passed field if non-nil, zero value otherwise.

### GetPassedOk

`func (o *MejoraloShipResponse) GetPassedOk() (*int32, bool)`

GetPassedOk returns a tuple with the Passed field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPassed

`func (o *MejoraloShipResponse) SetPassed(v int32)`

SetPassed sets Passed field to given value.


### GetTotal

`func (o *MejoraloShipResponse) GetTotal() int32`

GetTotal returns the Total field if non-nil, zero value otherwise.

### GetTotalOk

`func (o *MejoraloShipResponse) GetTotalOk() (*int32, bool)`

GetTotalOk returns a tuple with the Total field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotal

`func (o *MejoraloShipResponse) SetTotal(v int32)`

SetTotal sets Total field to given value.

### HasTotal

`func (o *MejoraloShipResponse) HasTotal() bool`

HasTotal returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


