# StoreResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**FactId** | **int32** |  | 
**Project** | **string** |  | 
**Message** | **string** |  | 

## Methods

### NewStoreResponse

`func NewStoreResponse(factId int32, project string, message string, ) *StoreResponse`

NewStoreResponse instantiates a new StoreResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewStoreResponseWithDefaults

`func NewStoreResponseWithDefaults() *StoreResponse`

NewStoreResponseWithDefaults instantiates a new StoreResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetFactId

`func (o *StoreResponse) GetFactId() int32`

GetFactId returns the FactId field if non-nil, zero value otherwise.

### GetFactIdOk

`func (o *StoreResponse) GetFactIdOk() (*int32, bool)`

GetFactIdOk returns a tuple with the FactId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFactId

`func (o *StoreResponse) SetFactId(v int32)`

SetFactId sets FactId field to given value.


### GetProject

`func (o *StoreResponse) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *StoreResponse) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *StoreResponse) SetProject(v string)`

SetProject sets Project field to given value.


### GetMessage

`func (o *StoreResponse) GetMessage() string`

GetMessage returns the Message field if non-nil, zero value otherwise.

### GetMessageOk

`func (o *StoreResponse) GetMessageOk() (*string, bool)`

GetMessageOk returns a tuple with the Message field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetMessage

`func (o *StoreResponse) SetMessage(v string)`

SetMessage sets Message field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


