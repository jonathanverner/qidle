== FEATURES ==

 - Code completion enhancements:

   -- when an opening ( is entered, show the __doc__ of the function DONE
   -- code completion for imports DONE
   -- when an opening [ is enetered following a dict, complete the list of keys DONE

 - Implement custom context-menu + actions

   -- delete a code/output block

 - Miscellanea

   - implement folding of blocks

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

 -  Check that a file being watched multiple times
     doesn't open multiple tabs (see 0b7d22378f1a8c838a714e4f791899a13f905649)

 -  Fix File Watches
     -- when watching a file, at first nothing is added to the watched_files menu
     -- reloading works only for the first change

 - Fix copy/paste

 - Fix sending objects over pipes


