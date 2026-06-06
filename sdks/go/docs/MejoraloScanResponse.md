# MejoraloScanResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Project** | **string** |  | 
**Score** | **int32** |  | 
**Stack** | **string** |  | 
**Dimensions** | [**[]DimensionResultModel**](DimensionResultModel.md) |  | 
**DeadCode** | **bool** |  | 
**TotalFiles** | Pointer to **int32** |  | [optional] [default to 0]
**TotalLoc** | Pointer to **int32** |  | [optional] [default to 0]
**FactId** | Pointer to **NullableInt32** |  | [optional] 

## Methods

### NewMejoraloScanResponse

`func NewMejoraloScanResponse(project string, score int32, stack string, dimensions []DimensionResultModel, deadCode bool, ) *MejoraloScanResponse`

NewMejoraloScanResponse instantiates a new MejoraloScanResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewMejoraloScanResponseWithDefaults

`func NewMejoraloScanResponseWithDefaults() *MejoraloScanResponse`

NewMejoraloScanResponseWithDefaults instantiates a new MejoraloScanResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetProject

`func (o *MejoraloScanResponse) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *MejoraloScanResponse) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *MejoraloScanResponse) SetProject(v string)`

SetProject sets Project field to given value.


### GetScore

`func (o *MejoraloScanResponse) GetScore() int32`

GetScore returns the Score field if non-nil, zero value otherwise.

### GetScoreOk

`func (o *MejoraloScanResponse) GetScoreOk() (*int32, bool)`

GetScoreOk returns a tuple with the Score field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetScore

`func (o *MejoraloScanResponse) SetScore(v int32)`

SetScore sets Score field to given value.


### GetStack

`func (o *MejoraloScanResponse) GetStack() string`

GetStack returns the Stack field if non-nil, zero value otherwise.

### GetStackOk

`func (o *MejoraloScanResponse) GetStackOk() (*string, bool)`

GetStackOk returns a tuple with the Stack field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetStack

`func (o *MejoraloScanResponse) SetStack(v string)`

SetStack sets Stack field to given value.


### GetDimensions

`func (o *MejoraloScanResponse) GetDimensions() []DimensionResultModel`

GetDimensions returns the Dimensions field if non-nil, zero value otherwise.

### GetDimensionsOk

`func (o *MejoraloScanResponse) GetDimensionsOk() (*[]DimensionResultModel, bool)`

GetDimensionsOk returns a tuple with the Dimensions field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDimensions

`func (o *MejoraloScanResponse) SetDimensions(v []DimensionResultModel)`

SetDimensions sets Dimensions field to given value.


### GetDeadCode

`func (o *MejoraloScanResponse) GetDeadCode() bool`

GetDeadCode returns the DeadCode field if non-nil, zero value otherwise.

### GetDeadCodeOk

`func (o *MejoraloScanResponse) GetDeadCodeOk() (*bool, bool)`

GetDeadCodeOk returns a tuple with the DeadCode field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetDeadCode

`func (o *MejoraloScanResponse) SetDeadCode(v bool)`

SetDeadCode sets DeadCode field to given value.


### GetTotalFiles

`func (o *MejoraloScanResponse) GetTotalFiles() int32`

GetTotalFiles returns the TotalFiles field if non-nil, zero value otherwise.

### GetTotalFilesOk

`func (o *MejoraloScanResponse) GetTotalFilesOk() (*int32, bool)`

GetTotalFilesOk returns a tuple with the TotalFiles field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalFiles

`func (o *MejoraloScanResponse) SetTotalFiles(v int32)`

SetTotalFiles sets TotalFiles field to given value.

### HasTotalFiles

`func (o *MejoraloScanResponse) HasTotalFiles() bool`

HasTotalFiles returns a boolean if a field has been set.

### GetTotalLoc

`func (o *MejoraloScanResponse) GetTotalLoc() int32`

GetTotalLoc returns the TotalLoc field if non-nil, zero value otherwise.

### GetTotalLocOk

`func (o *MejoraloScanResponse) GetTotalLocOk() (*int32, bool)`

GetTotalLocOk returns a tuple with the TotalLoc field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalLoc

`func (o *MejoraloScanResponse) SetTotalLoc(v int32)`

SetTotalLoc sets TotalLoc field to given value.

### HasTotalLoc

`func (o *MejoraloScanResponse) HasTotalLoc() bool`

HasTotalLoc returns a boolean if a field has been set.

### GetFactId

`func (o *MejoraloScanResponse) GetFactId() int32`

GetFactId returns the FactId field if non-nil, zero value otherwise.

### GetFactIdOk

`func (o *MejoraloScanResponse) GetFactIdOk() (*int32, bool)`

GetFactIdOk returns a tuple with the FactId field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetFactId

`func (o *MejoraloScanResponse) SetFactId(v int32)`

SetFactId sets FactId field to given value.

### HasFactId

`func (o *MejoraloScanResponse) HasFactId() bool`

HasFactId returns a boolean if a field has been set.

### SetFactIdNil

`func (o *MejoraloScanResponse) SetFactIdNil(b bool)`

 SetFactIdNil sets the value for FactId to be an explicit nil

### UnsetFactId
`func (o *MejoraloScanResponse) UnsetFactId()`

UnsetFactId ensures that no value is present for FactId, not even an explicit nil

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


