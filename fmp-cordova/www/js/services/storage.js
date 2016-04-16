fmpApp.factory('FmpLocalStorage', function(){
  var logger = new Logger("FmpLocalStorage", false);
  var methods = {};

  methods.getColKey = function(storageField) {
    if (typeof storageField == "string") {
      return storageField;
    }
    if (typeof storageField == "object") {
      return storageField.collectionKey;
    }
  };

  methods.getStoreKey = function(storageField) {
    if (typeof storageField == "string") {
      return storageField;
    }
    if (typeof storageField == "object") {
      return storageField.storageKey;
    }
  };

  methods.saveInt = function(collection) {
    if (typeof collection.storeFields.ints == 'undefined' ||
        !collection.storeFields.ints ||
        collection.storeFields.ints.length == 0) {
      return;
    }

    for(var i=0;i<collection.storeFields.ints.length;i++){
      var colKey = methods.getColKey(collection.storeFields.ints[i]),
          storeKey = methods.getStoreKey(collection.storeFields.ints[i]);

      if (typeof collection[colKey] == 'undefined') {
        console.error("FmpLocalStorage saveInt undefined:", colKey);
        continue;
      }
      try {
        localStorage[storeKey] = parseInt(collection[colKey]);
      } catch (e) {
        console.error("FmpLocalStorage.saveInt() error converting to int key:", colKey,
                      "value:", collection[colKey], e);
      }
    }
  };

  methods.loadInt = function(collection) {
    if (typeof collection.storeFields.ints == 'undefined' || !collection.storeFields.ints ||
        collection.storeFields.ints.length == 0) {
      return;
    }
    for(var i=0;i<collection.storeFields.ints.length;i++){
      var colKey = methods.getColKey(collection.storeFields.ints[i]),
          storeKey = methods.getStoreKey(collection.storeFields.ints[i]);

      if (typeof localStorage[storeKey] == 'undefined') {
        console.error("FmpLocalStorage loadInt undefined:", storeKey);
        continue;
      }
      try {
        collection[colKey] = parseInt(localStorage[storeKey]);
      } catch (e) {
        console.error("FmpLocalStorage.loadInt() error converting to int key:",
                      storeKey, "value:", localStorage[storeKey], e);
      }
    }
  };

  methods.saveFloat = function(collection) {
    if (typeof collection.storeFields.floats == 'undefined' || !collection.storeFields.floats ||
        collection.storeFields.floats.length == 0) {
      return;
    }

    for(var i=0;i<collection.storeFields.floats.length;i++){
      var colKey = methods.getColKey(collection.storeFields.floats[i]),
          storeKey = methods.getStoreKey(collection.storeFields.floats[i]);
      if (typeof collection[colKey] == 'undefined') {
        console.error("FmpLocalStorage saveFloat undefined:", colKey);
        continue;
      }
      try {
        localStorage[storeKey] = parseFloat(collection[colKey]);
      } catch (e) {
        console.error("FmpLocalStorage.saveFloat() error converting float colKey:",
                      colKey, "value:", collection[colKey], e);
      }
    }
  };

  methods.loadFloat = function(collection) {
    if (typeof collection.storeFields.floats == 'undefined' ||
        !collection.storeFields.floats ||
        collection.storeFields.floats.length == 0) {
      return;
    }
    for(var i=0;i<collection.storeFields.floats.length;i++){
      var colKey = methods.getColKey(collection.storeFields.floats[i]),
          storeKey = methods.getStoreKey(collection.storeFields.floats[i]);
      if (typeof localStorage[storeKey] == 'undefined') {
        console.error("FmpLocalStorage loadFloat undefined:", storeKey);
        continue;
      }
      try {
        collection[colKey] = parseFloat(localStorage[storeKey]);
      } catch (e) {
        console.error("FmpLocalStorage.loadFloat() error converting to float storeKey:",
                      storeKey, "value:", localStorage[storeKey], e);
      }
    }
  };

  methods.saveString = function(collection) {
    if (typeof collection.storeFields.strings == 'undefined' ||
        !collection.storeFields.strings ||
        collection.storeFields.strings.length == 0) {
      return;
    }

    for(var i=0;i<collection.storeFields.strings.length;i++){
      var colKey = methods.getColKey(collection.storeFields.strings[i]),
          storeKey = methods.getStoreKey(collection.storeFields.strings[i]);
      if (typeof collection[colKey] == 'undefined') {
        console.error("FmpLocalStorage saveString undefined:", colKey);
        continue;
      }
      try {
        localStorage[storeKey] = collection[colKey]+"";
      } catch (e) {
        console.error("FmpLocalStorage.saveString() error converting string colKey:",
                      colKey, "value:", collection[colKey], e);
      }
    }
  };

  methods.loadString = function(collection) {
    if (typeof collection.storeFields.strings == 'undefined' ||
        !collection.storeFields.strings ||
        collection.storeFields.strings.length == 0) {
      return;
    }
    for(var i=0;i<collection.storeFields.strings.length;i++){
      var colKey = methods.getColKey(collection.storeFields.strings[i]),
          storeKey = methods.getStoreKey(collection.storeFields.strings[i]);
      if (typeof localStorage[storeKey] == 'undefined') {
        console.error("FmpLocalStorage loadString undefined:", storeKey);
        continue;
      }
      try {
        collection[colKey] = localStorage[storeKey]+"";
      } catch (e) {
        console.error("FmpLocalStorage.loadString() error converting to string storeKey:",
                      storeKey, "value:", localStorage[storeKey], e);
      }
    }
  };

  methods.saveObject = function(collection) {
    if (typeof collection.storeFields.objects == 'undefined' ||
        !collection.storeFields.objects ||
        collection.storeFields.objects.length == 0) {
      return;
    }

    for(var i=0;i<collection.storeFields.objects.length;i++){
      var colKey = methods.getColKey(collection.storeFields.objects[i]),
          storeKey = methods.getStoreKey(collection.storeFields.objects[i]);
      if (typeof collection[colKey] == 'undefined') {
        console.error("FmpLocalStorage saveObject undefined:", colKey);
        continue;
      }
      try {
        localStorage[storeKey] = JSON.stringify(collection[colKey]);
      } catch (e) {
        console.error("FmpLocalStorage.saveObject() error converting to object storeKey:",
                      colKey, "value:", collection[colKey], e);
      }
    }
  };

  methods.loadObject = function(collection) {
    if (typeof collection.storeFields.objects == 'undefined' ||
        !collection.storeFields.objects ||
        collection.storeFields.objects.length == 0) {
      return;
    }
    for(var i=0;i<collection.storeFields.objects.length;i++){
      var colKey = methods.getColKey(collection.storeFields.objects[i]),
          storeKey = methods.getStoreKey(collection.storeFields.objects[i]);
      if (typeof localStorage[storeKey] == 'undefined') {
        console.error("FmpLocalStorage loadObject undefined:", storeKey);
        continue;
      }
      try {
        collection[colKey] = JSON.parse(localStorage[storeKey]);
      } catch (e) {
        console.error("FmpLocalStorage.loadObject() error converting to object storeKey:",
                      storeKey, "value:", localStorage[storeKey], e);
        if (localStorage[storeKey].indexOf(",") != -1) {
          try {
            var val = parseInt(localStorage[storeKey]);
            console.error("Fallback parse worked.");
            collection[colKey] = [val];
          } catch(e) {
            console.error("Error with parsing:0", e);
            continue;
          }
        }
        // This is fallback code to handle old style of list.
        // it was 1,2,3,4,5 and a string.  I've decided to store it
        // as a list & JSON.
        var objectRx = /^\{.*\}$/,
            arrayRx = /^\[.*\]$/;

        // It doesn't appear to be [] or {}
        if (!objectRx.test(localStorage[storeKey]) &&
            !arrayRx.test(localStorage[storeKey])) {
          // It doesn't appear to be an object or an array.
          var values = localStorage[storeKey].split(","),
              list = [],
              allInts = true;
          for(var i2=0;i2<values.length;i2++) {
            try {
              var val = parseInt(values[i2]);
              list.push(val);
            } catch(e) {
              console.error("Fallback error");
              allInts = false;
              break;
            }
          }
          // Try the next storeField.
          if (!allInts) {
            continue;
          }
          collection[colKey] = list;
        }
      }
    }
  };

  methods.save = function(collection) {
    if (typeof collection.storeFields == 'undefined' ||
        !collection.storeFields) {
      log.error("FmpLocalStorage.save() collection.storeFields missing:", collection);
      return;
    }
    methods.saveInt(collection);
    methods.saveFloat(collection);
    methods.saveString(collection);
    methods.saveObject(collection);
  }

  methods.load = function(collection) {
    if (typeof collection.storeFields == 'undefined') {
      log.error("FmpLocalStorage.load() collection.storeFields missing:", collection);
      return;
    }
    methods.loadInt(collection);
    methods.loadFloat(collection);
    methods.loadString(collection);
    methods.loadObject(collection);
  };

  logger.log("initialized");
  return methods;

});