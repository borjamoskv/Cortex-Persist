# TimeSummaryResponse

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**TotalSeconds** | **int32** |  | 
**TotalHours** | **float32** |  | 
**ByCategory** | **map[string]int32** |  | 
**ByProject** | **map[string]int32** |  | 
**Entries** | **int32** |  | 
**Heartbeats** | **int32** |  | 
**TopEntities** | **[][]interface{}** |  | 

## Methods

### NewTimeSummaryResponse

`func NewTimeSummaryResponse(totalSeconds int32, totalHours float32, byCategory map[string]int32, byProject map[string]int32, entries int32, heartbeats int32, topEntities [][]interface{}, ) *TimeSummaryResponse`

NewTimeSummaryResponse instantiates a new TimeSummaryResponse object
This constructor will assign default values to properties that have it defined,
and makes sure properties required by API are set, but the set of arguments
will change when the set of required properties is changed

### NewTimeSummaryResponseWithDefaults

`func NewTimeSummaryResponseWithDefaults() *TimeSummaryResponse`

NewTimeSummaryResponseWithDefaults instantiates a new TimeSummaryResponse object
This constructor will only assign default values to properties that have it defined,
but it doesn't guarantee that properties required by API are set

### GetTotalSeconds

`func (o *TimeSummaryResponse) GetTotalSeconds() int32`

GetTotalSeconds returns the TotalSeconds field if non-nil, zero value otherwise.

### GetTotalSecondsOk

`func (o *TimeSummaryResponse) GetTotalSecondsOk() (*int32, bool)`

GetTotalSecondsOk returns a tuple with the TotalSeconds field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalSeconds

`func (o *TimeSummaryResponse) SetTotalSeconds(v int32)`

SetTotalSeconds sets TotalSeconds field to given value.


### GetTotalHours

`func (o *TimeSummaryResponse) GetTotalHours() float32`

GetTotalHours returns the TotalHours field if non-nil, zero value otherwise.

### GetTotalHoursOk

`func (o *TimeSummaryResponse) GetTotalHoursOk() (*float32, bool)`

GetTotalHoursOk returns a tuple with the TotalHours field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTotalHours

`func (o *TimeSummaryResponse) SetTotalHours(v float32)`

SetTotalHours sets TotalHours field to given value.


### GetByCategory

`func (o *TimeSummaryResponse) GetByCategory() map[string]int32`

GetByCategory returns the ByCategory field if non-nil, zero value otherwise.

### GetByCategoryOk

`func (o *TimeSummaryResponse) GetByCategoryOk() (*map[string]int32, bool)`

GetByCategoryOk returns a tuple with the ByCategory field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetByCategory

`func (o *TimeSummaryResponse) SetByCategory(v map[string]int32)`

SetByCategory sets ByCategory field to given value.


### GetByProject

`func (o *TimeSummaryResponse) GetByProject() map[string]int32`

GetByProject returns the ByProject field if non-nil, zero value otherwise.

### GetByProjectOk

`func (o *TimeSummaryResponse) GetByProjectOk() (*map[string]int32, bool)`

GetByProjectOk returns a tuple with the ByProject field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetByProject

`func (o *TimeSummaryResponse) SetByProject(v map[string]int32)`

SetByProject sets ByProject field to given value.


### GetEntries

`func (o *TimeSummaryResponse) GetEntries() int32`

GetEntries returns the Entries field if non-nil, zero value otherwise.

### GetEntriesOk

`func (o *TimeSummaryResponse) GetEntriesOk() (*int32, bool)`

GetEntriesOk returns a tuple with the Entries field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetEntries

`func (o *TimeSummaryResponse) SetEntries(v int32)`

SetEntries sets Entries field to given value.


### GetHeartbeats

`func (o *TimeSummaryResponse) GetHeartbeats() int32`

GetHeartbeats returns the Heartbeats field if non-nil, zero value otherwise.

### GetHeartbeatsOk

`func (o *TimeSummaryResponse) GetHeartbeatsOk() (*int32, bool)`

GetHeartbeatsOk returns a tuple with the Heartbeats field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetHeartbeats

`func (o *TimeSummaryResponse) SetHeartbeats(v int32)`

SetHeartbeats sets Heartbeats field to given value.


### GetTopEntities

`func (o *TimeSummaryResponse) GetTopEntities() [][]interface{}`

GetTopEntities returns the TopEntities field if non-nil, zero value otherwise.

### GetTopEntitiesOk

`func (o *TimeSummaryResponse) GetTopEntitiesOk() (*[][]interface{}, bool)`

GetTopEntitiesOk returns a tuple with the TopEntities field if it's non-nil, zero value otherwise
and a boolean to check if the value has been set.

### SetTopEntities

`func (o *TimeSummaryResponse) SetTopEntities(v [][]interface{})`

SetTopEntities sets TopEntities field to given value.



[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


