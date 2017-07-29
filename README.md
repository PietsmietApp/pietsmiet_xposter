# Backend for the [Pietsmiet-App](https://github.com/l3d00m/pietsmiet_android)

Processes pietsmiet.de feeds (Uploadplan, News, Videos, Pietcast):

* Load feed descriptions from the direct URL
* Store in Firebase Database
* Send a Firebase Cloud Message
* Upload thumbnails of Video to Firebase Storage
* Crosspost Uploadplan to http://reddit.com/r/pietsmiet
* Checks for edits of the Uploadplan
* Removes deleted items from the database

See also: [Old commit history of repository](https://github.com/l3d00m/pietsmiet_android/commits/12107d7efcfb22ffb07827a75a61214edfac1bea/backend)
