#!/usr/bin/env python
# lib/crumbs.py -- Create crumb type list
#    Copyright (C) 2013 Eugene Miller <theerm@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import gtk, gobject, sys, random
from __init__ import gtk_main_quit

class Crumbs(gtk.VBox):
    def __init__(self, target_width = 600):
        gtk.VBox.__init__(self)
        self.straighten_lock = False
        self.allocation_lock = False
        self.show_all()
        self.target_width = target_width
        self.pack_start(gtk.HBox(),False,False)
        self.connect("size-allocate", self.on_allocate)

    def on_allocate(self, widget, allocation):
        if self.allocation_lock or self.straighten_lock:
            return
        self.allocation_lock = True
        parent = self.get_parent()
        parent_allocation = parent.get_allocation()
        self.target_width = parent_allocation.width
        self.straighten()
        self.allocation_lock = False

    def add_crumb(self, widget, idx=None):
        parent = self.get_parent()
        if parent:
            # Change target_width to parent's allocation.
            parent_allocation = parent.get_allocation()
            self.target_width = parent_allocation.width

        # Ensure there is at least 1 empty row.
        children = self.get_children()
        if not children:
            # Add new row.
            self.pack_start(gtk.HBox(),False,False)
            children = self.get_children()

        last_row = children[-1]
        width, height = last_row.size_request()
        if width >= self.target_width:
            # Add another row because the last row is too wide.
            self.pack_start(gtk.HBox(),False,False)
            children = self.get_children()
            last_row = children[-1]

        last_row.show() # makes sure the last row is showing (we could have added a row.)
        widget.show()

        # Add widget to crumbs.
        last_row.pack_start(widget, False, False)
        self.straighten()

    def insert_crumb(self,widget, idx):
        rows = self.get_children()
        widget.show()

        if idx < 0:
            cnt = 1
            for r in rows:
                for c in r.get_children():
                    cnt = cnt + 1
            idx = cnt + idx

        if idx < 0:
            idx = 0

        cnt = 0
        inserted = False
        for r in rows:
            for c in r.get_children():
                if idx == cnt:
                    inserted = True
                    r.pack_start(widget,False,False)
                    r.reorder_child(widget, idx)
                    break
                cnt = cnt + 1

        if not inserted:
            children = self.get_children()
            last_row = children[-1]
            last_row.pack_start(widget, False,False)

        self.straighten()

    def straighten(self):
        if self.straighten_lock:
            return
        self.straighten_lock = True
        rebuild = False
        rows = self.get_children()
        for i, row in enumerate(rows):
            row_width, r_height = row.size_request()
            crumbs = row.get_children()
            if not crumbs:
                # Don't process empty rows.
                continue

            try:
                next_row_children = rows[i+1].get_children()
            except IndexError, err:
                self.pack_start(gtk.HBox(), False, False)
                rows = self.get_children()
                rows[i+1].show()
                next_row_children = rows[i+1].get_children()

            if row_width >= self.target_width:
                if len(crumbs) == 1:
                    # The crumb takes up the entire row so we do nothing.
                    continue
                c = crumbs[-1]
                # Remove the last crumb from the current row, and add it to the
                # next row
                rebuild = True
                row.remove(c)
                rows[i+1].pack_start(c, False, False)
                rows[i+1].reorder_child(c, 0)
                c.show()

            elif row_width < self.target_width and next_row_children:
                # Next row has children, and the current row's width
                # is < our target_width
                next_row_first_child = next_row_children[0]
                next_row_first_child_width, c_height = next_row_first_child.size_request()
                if (next_row_first_child_width + row_width) < self.target_width:
                    # the next row's first child will fit into the current row.
                    # remove it from the next row, and add it to the current row.
                    rebuild = True
                    rows[i+1].remove(next_row_first_child)
                    row.pack_start(next_row_first_child,False,False)
                    next_row_first_child.show()
                    if not rows[i+1].get_children():
                        # the next row has no children so we remove it.
                        rows[i+1].destroy()

        self.straighten_lock = False
        if rebuild:
            # run straighten again to ensure crumbs are in the right place.
            self.straighten()


if __name__ == '__main__':

    def on_remove(w, crumb, text):
        print "removing:",text
        crumb.destroy()

    def on_info(w, crumb, text):
        print "This does nothing, but here's where you'd do a db lookup about that tag."
        print "text:",text

    w = gtk.Window()
    w.set_default_size(600, 400)
    w.set_position(gtk.WIN_POS_CENTER)

    crbs = Crumbs()
    crbs.target_width = 600
    crbs.show_all()
    
    if "-vbox" in sys.argv:
        # This is for testing behavior in a vbox
        container = gtk.VBox()
        container.pack_start(crbs, False, False)
    elif "-hbox" in sys.argv:
        # This is for testing behavior in a hbox
        container = gtk.HBox()
        container.pack_start(crbs, True, True) # hboxes work better with True,True
    else:
        # By default use a scrolled window for the container
        container = gtk.ScrolledWindow()
        container.set_policy(gtk.POLICY_AUTOMATIC,gtk.POLICY_AUTOMATIC)
        container.add_with_viewport(crbs)

    

    crumb_list = [
        "Allison Krauss Yo-yo Ma, Edgar Meyer, Mark O'connor",
        "Yo-Yo Ma, Edgar Meyer, Mark O'Connor",
        "Yo-Yo Ma",
        "Edgar Meyer",
        "Mark O'Connor",
        "Allison Krauss Yo-yo Ma",
        "Mark O'connor",
    ]
    random.shuffle(crumb_list)

    for i, t in enumerate(crumb_list):
        # create buttons out of crumb_list text

        # Setup event boxes so we have a little bit of style for our buttons.
        # (two buttons next to each other looks kinda crappy)
        border = gtk.EventBox()
        border.show()
        border.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
        border.set_border_width(1) # padding so there is space between our buttons.

        body = gtk.EventBox()
        body.show()
        body.set_border_width(1) # padding so black shows.

        # Style our buttons.
        body.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("white"))
        body.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))

        hbox = gtk.HBox() # For putting out buttons into.
        hbox.show()

        ## Tag button
        btn = gtk.Button()
        btn.set_property("relief",gtk.RELIEF_NONE) # Remove default borders
        btn.set_label("%s %s" % (i,t)) # Add i debugging.
        btn.connect("activate", on_info, border, t)
        btn.connect("pressed", on_info, border, t)
        btn.show()
        hbox.pack_start(btn,True,True)

        ## Remove button
        close_image = gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
        btn = gtk.Button()
        btn.set_property("relief",gtk.RELIEF_NONE) # Remove default borders
        btn.set_image(close_image)
        btn.set_image_position(gtk.POS_RIGHT)
        btn.connect("activate", on_remove, border, t)
        btn.connect("pressed", on_remove, border, t)
        btn.show()
        hbox.pack_end(btn,False,False)

        border.add(body)
        body.add(hbox)
        crbs.add_crumb(border)

    container.show()
    w.add(container)
    w.connect("destroy", gtk_main_quit)
    w.show()
    gtk.main()


