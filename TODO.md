== FEATURES ==

 - Code completion enhancements:

   -- when an opening ( is entered, show the __doc__ of the function DONE
   -- when an opening [ is enetered following a dict, complete the list of keys DONE
   -- code completion for imports PARTIALLY DONE

 - Implement custom context-menu + actions

   -- delete a code/output block

 - Miscellanea

   - implement folding of blocks

 - Session saving
   -- save history/output/both
   -- save session

 - Debugger

 - Menus ...

   -- embed kate's menus
   -- add gui config
   -- open output in a new editor
   -- open code in new editor

 - Custom shells

   -- make it possibile for the user to provide custom hooks preprocessing code
      before it is executed

   -- implement bash-like mode

   -- implement gnuplot like mode


== BUG FIXES ==

 -  Fix File Watches
     -- when watching a file, at first nothing is added to the watched_files menu
     -- reloading works only for the first change

 - Fix copy/paste

 - Fix showing images (for some reason, they seem to share the same data,
   when this get's garbage collected, it eventually leads to corrupted
   pictures and crashes)


