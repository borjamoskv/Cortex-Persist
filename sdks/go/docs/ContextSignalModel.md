# ContextSignalModel

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**Source** | **string** |  | 
**SignalType** | **string** |  | 
**Content** | **string** |  | 
**Project** | Pointer to **NullableString** |  | [optional] 
**Timestamp** | **string** |  | 
**Weight** | **float32** |  | 

## Methods

### NewContextSignalModel

`func NewContextSignalModel(source string, signalType string, content string, timestamp string, weight float32, ) *ContextSignalModel`

NewContextSignalModel instantiates a new ContextSignalModel object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewContextSignalModelWithDefaults

`func NewContextSignalModelWithDefaults() *ContextSignalModel`

NewContextSignalModelWithDefaults instantiates a new ContextSignalModel object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetSource

`func (o *ContextSignalModel) GetSource() string`

GetSource returns the Source field if non-nil, zero value otherwise.

### GetSourceOk

`func (o *ContextSignalModel) GetSourceOk() (*string, bool)`

GetSourceOk returns a tuple with the Source field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSource

`func (o *ContextSignalModel) SetSource(v string)`

SetSource sets Source field to given value.


### GetSignalType

`func (o *ContextSignalModel) GetSignalType() string`

GetSignalType returns the SignalType field if non-nil, zero value otherwise.

### GetSignalTypeOk

`func (o *ContextSignalModel) GetSignalTypeOk() (*string, bool)`

GetSignalTypeOk returns a tuple with the SignalType field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetSignalType

`func (o *ContextSignalModel) SetSignalType(v string)`

SetSignalType sets SignalType field to given value.


### GetContent

`func (o *ContextSignalModel) GetContent() string`

GetContent returns the Content field if non-nil, zero value otherwise.

### GetContentOk

`func (o *ContextSignalModel) GetContentOk() (*string, bool)`

GetContentOk returns a tuple with the Content field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetContent

`func (o *ContextSignalModel) SetContent(v string)`

SetContent sets Content field to given value.


### GetProject

`func (o *ContextSignalModel) GetProject() string`

GetProject returns the Project field if non-nil, zero value otherwise.

### GetProjectOk

`func (o *ContextSignalModel) GetProjectOk() (*string, bool)`

GetProjectOk returns a tuple with the Project field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetProject

`func (o *ContextSignalModel) SetProject(v string)`

SetProject sets Project field to given value.

### HasProject

`func (o *ContextSignalModel) HasProject() bool`

HasProject returns a boolean if a field has been set.

### SetProjectNil

`func (o *ContextSignalModel) SetProjectNil(b bool)`

 SetProjectNil sets the value for Project to be an explicit nil

### UnsetProject
`func (o *ContextSignalModel) UnsetProject()`

UnsetProject ensures that no value is present for Project, not even an explicit nil
### GetTimestamp

`func (o *ContextSignalModel) GetTimestamp() string`

GetTimestamp returns the Timestamp field if non-nil, zero value otherwise.

### GetTimestampOk

`func (o *ContextSignalModel) GetTimestampOk() (*string, bool)`

GetTimestampOk returns a tuple with the Timestamp field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTimestamp

`func (o *ContextSignalModel) SetTimestamp(v string)`

SetTimestamp sets Timestamp field to given value.


### GetWeight

`func (o *ContextSignalModel) GetWeight() float32`

GetWeight returns the Weight field if non-nil, zero value otherwise.

### GetWeightOk

`func (o *ContextSignalModel) GetWeightOk() (*float32, bool)`

GetWeightOk returns a tuple with the Weight field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetWeight

`func (o *ContextSignalModel) SetWeight(v float32)`

SetWeight sets Weight field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


