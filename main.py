diff --git a/main.py b/main.py
index e4881ae..b1scroll 100644
--- a/main.py
+++ b/main.py
@@
-from tkinter import ttk, scrolledtext, messagebox, simpledialog
+from tkinter import ttk, scrolledtext, messagebox, simpledialog
+from utils.scrollable import ScrollableFrame
@@
-            # Configuration tab
-            config_tab = ttk.Frame(notebook)
-            notebook.add(config_tab, text="Configuration")
-            self._create_config_tab(config_tab)
+            # Configuration tab (scrollable)
+            _cfg_tab = ttk.Frame(notebook)
+            notebook.add(_cfg_tab, text="Configuration")
+            cfg_scroll = ScrollableFrame(_cfg_tab)
+            cfg_scroll.pack(fill=tk.BOTH, expand=True)
+            self._create_config_tab(cfg_scroll.container)
@@
-            # Bot Management tab (NEW!)
-            bot_mgmt_tab = ttk.Frame(notebook)
-            notebook.add(bot_mgmt_tab, text="Bot Management")
-            self._create_bot_management_tab(bot_mgmt_tab)
+            # Bot Management tab (scrollable)
+            _bot_tab = ttk.Frame(notebook)
+            notebook.add(_bot_tab, text="Bot Management")
+            bot_scroll = ScrollableFrame(_bot_tab)
+            bot_scroll.pack(fill=tk.BOTH, expand=True)
+            self._create_bot_management_tab(bot_scroll.container)
@@
-            # Groups tab
-            groups_tab = ttk.Frame(notebook)
-            notebook.add(groups_tab, text="Groups")
-            self._create_groups_tab(groups_tab)
+            # Groups tab (scrollable)
+            _grp_tab = ttk.Frame(notebook)
+            notebook.add(_grp_tab, text="Groups")
+            grp_scroll = ScrollableFrame(_grp_tab)
+            grp_scroll.pack(fill=tk.BOTH, expand=True)
+            self._create_groups_tab(grp_scroll.container)
