# TelemetryPayload

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**TelemetryLogs** | Pointer to **[]map[string]interface{}** |  | [optional] 
**NewEdges** | Pointer to **map[string]float32** |  | [optional] 
**AuthorsDelta** | Pointer to **map[string]map[string]interface{}** |  | [optional] 

## Methods

### NewTelemetryPayload

`func NewTelemetryPayload() *TelemetryPayload`

NewTelemetryPayload instantiates a new TelemetryPayload object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewTelemetryPayloadWithDefaults

`func NewTelemetryPayloadWithDefaults() *TelemetryPayload`

NewTelemetryPayloadWithDefaults instantiates a new TelemetryPayload object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetTelemetryLogs

`func (o *TelemetryPayload) GetTelemetryLogs() []*map[string]interface{}`

GetTelemetryLogs returns the TelemetryLogs field if non-nil, zero value otherwise.

### GetTelemetryLogsOk

`func (o *TelemetryPayload) GetTelemetryLogsOk() (*[]*map[string]interface{}, bool)`

GetTelemetryLogsOk returns a tuple with the TelemetryLogs field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTelemetryLogs

`func (o *TelemetryPayload) SetTelemetryLogs(v []*map[string]interface{})`

SetTelemetryLogs sets TelemetryLogs field to given value.

### HasTelemetryLogs

`func (o *TelemetryPayload) HasTelemetryLogs() bool`

HasTelemetryLogs returns a boolean if a field has been set.

### GetNewEdges

`func (o *TelemetryPayload) GetNewEdges() map[string]float32`

GetNewEdges returns the NewEdges field if non-nil, zero value otherwise.

### GetNewEdgesOk

`func (o *TelemetryPayload) GetNewEdgesOk() (*map[string]float32, bool)`

GetNewEdgesOk returns a tuple with the NewEdges field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetNewEdges

`func (o *TelemetryPayload) SetNewEdges(v map[string]float32)`

SetNewEdges sets NewEdges field to given value.

### HasNewEdges

`func (o *TelemetryPayload) HasNewEdges() bool`

HasNewEdges returns a boolean if a field has been set.

### GetAuthorsDelta

`func (o *TelemetryPayload) GetAuthorsDelta() map[string]map[string]interface{}`

GetAuthorsDelta returns the AuthorsDelta field if non-nil, zero value otherwise.

### GetAuthorsDeltaOk

`func (o *TelemetryPayload) GetAuthorsDeltaOk() (*map[string]map[string]interface{}, bool)`

GetAuthorsDeltaOk returns a tuple with the AuthorsDelta field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetAuthorsDelta

`func (o *TelemetryPayload) SetAuthorsDelta(v map[string]map[string]interface{})`

SetAuthorsDelta sets AuthorsDelta field to given value.

### HasAuthorsDelta

`func (o *TelemetryPayload) HasAuthorsDelta() bool`

HasAuthorsDelta returns a boolean if a field has been set.


[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


