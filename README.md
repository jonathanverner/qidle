# Q-idle #

Q-idle is a Qt version of the Idle IDE for Python.
It runs code in a different process and thus allows easier interruption
of the shell (and long running code does not freeze the interface).

## Features ##

  - syntax hilighting
  - code completion, dict key & filename completion
  - \_\_doc\_\_ and function signature tooltips
  - reload file on change (just open a file or drag and drop it onto the shell window)
  - pretty printing of objects (extensible via plugins)
    -- pylab.figure, QtGui.QImage, PIL.Image (images, yay :-))
  - basic editor with code completion based on jedi
  - multiple editor tabs
  - automatic shell input/output history saving/reloading

## Planned Features ##

  - session saving
  - inspection tools
  - debugger


