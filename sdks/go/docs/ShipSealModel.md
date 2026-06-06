# ShipSealModel

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Name** | **string** |  | 
**Passed** | **bool** |  | 
**Detail** | Pointer to **string** |  | [optional] [default to ""]

## Methods

### NewShipSealModel

`func NewShipSealModel(name string, passed bool, ) *ShipSealModel`

NewShipSealModel instantiates a new ShipSealModel object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewShipSealModelWithDefaults

`func NewShipSealModelWithDefaults() *ShipSealModel`

NewShipSealModelWithDefaults instantiates a new ShipSealModel object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetName

`func (o *ShipSealModel) GetName() string`

GetName returns the Name field if non-nil, zero value otherwise.

### GetNameOk

`func (o *ShipSealModel) GetNameOk() (*string, bool)`

GetNameOk returns a tuple with the Name field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetName

`func (o *ShipSealModel) SetName(v string)`

SetName sets Name field to given value.


### GetPassed

`func (o *ShipSealModel) GetPassed() bool`

GetPassed returns the Passed field if non-nil, zero value otherwise.

### GetPassedOk

`func (o *ShipSealModel) GetPassedOk() (*bool, bool)`

GetPassedOk returns a tuple with the Passed field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetPassed

`func (o *ShipSealModel) SetPassed(v bool)`

SetPassed sets Passed field to given value.


### GetDetail

`func (o *ShipSealModel) GetDetail() string`

GetDetail returns the Detail field if non-nil, zero value otherwise.

### GetDetailOk

`func (o *ShipSealModel) GetDetailOk() (*string, bool)`

GetDetailOk returns a tuple with the Detail field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDetail

`func (o *ShipSealModel) SetDetail(v string)`

SetDetail sets Detail field to given value.

### HasDetail

`func (o *ShipSealModel) HasDetail() bool`

HasDetail returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


