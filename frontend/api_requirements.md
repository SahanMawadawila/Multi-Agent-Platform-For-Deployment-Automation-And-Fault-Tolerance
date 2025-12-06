# API Requirements

## Get Project List

> **Endpoint:** `GET <NEXT_PUBLIC_API_END_POINT>/api/projects`

> **Response:**
```json
[
  {
    "id": "string",
    "name": "string",
    "description": "string",
    "createdAt": "string (ISO 8601 date)",
    "updatedAt": "string (ISO 8601 date)"
  }
]
```
> Status Code: 200 OK


On Error:
```json
{
  "error": "string"
}
```
with non-200 HTTP status code.


## Check Git Repository is Accessible
> **Endpoint:** `GET <NEXT_PUBLIC_API_END_POINT>/api/projects/:id/git`


## Create New Project
> **Endpoint:** `POST <NEXT_PUBLIC_API_END_POINT>/api/projects`
> **Request Body:**
```json
{
  "name": "string",
  "repoUrl": "string",
  "projectType": "single" | "microservice"
}
```
> **Response:**
```json
{
  "id": "string",
  "redirectUrl": "string"
}
```
> Status Code: 201 Created

On Error:
```json
{
  "error": "string"
}
```
with non-201 HTTP status code.


## Connect with GitHub (for private repositories)
> **Endpoint:** `POST <NEXT_PUBLIC_API_END_POINT>/api/integrations/github/connect`
> **Request Body:**
```json
{
  "repoUrl": "string"
}
```
> **Response:**
```json
{
  "authUrl": "string" // URL to redirect user for GitHub OAuth
}
```
> Status Code: 200 OK

On Error:
```json
{
  "error": "string"
}
```
with non-200 HTTP status code.